// facemarks: every face in a video, sampled at a fixed rate, with how open its mouth is and where its head points
// (Apple Vision face landmarks, on-device). The podcast pipeline's active-speaker signal: with one camera and one mic,
// the person talking is the one whose mouth moves (kit/podcast/speakers.py).
//
//   swiftc -O -o kit/bin/facemarks kit/podcast/facemarks.swift
//   kit/bin/facemarks <video> <out.jsonl> [samples per second, default 10]
//
// Each line: {"t": s, "faces": [{"x","y","w","h" (0..1, top-left origin), "mouth" (inner-lip gap / face height),
// "pitch", "yaw" (radians, Vision's estimate; often 0), "eyes" (eye openness: low = looking down)}]}.
import AVFoundation
import Foundation
import Vision

let a = CommandLine.arguments
guard a.count >= 3 else { FileHandle.standardError.write("usage: facemarks <video> <out.jsonl> [fps]\n".data(using: .utf8)!); exit(1) }
let rate = a.count > 3 ? (Double(a[3]) ?? 10) : 10
let asset = AVURLAsset(url: URL(fileURLWithPath: a[1]))
let sem = DispatchSemaphore(value: 0)
var track: AVAssetTrack?
var natural = CGSize(width: 1920, height: 1080)              // the stored (raw) frame size: the reader decodes these
var orient = CGImagePropertyOrientation.up                    // how the player turns them (iPhone: often 180 or 90)
Task {
  track = try? await asset.loadTracks(withMediaType: .video).first
  if let t = track, let s = try? await t.load(.naturalSize), let tf = try? await t.load(.preferredTransform) {
    natural = CGSize(width: abs(s.width), height: abs(s.height))
    let deg = Int((atan2(Double(tf.b), Double(tf.a)) * 180 / Double.pi).rounded())
    switch (deg + 360) % 360 { case 90: orient = .right; case 180: orient = .down; case 270: orient = .left; default: orient = .up }
  }
  sem.signal()
}
sem.wait()
guard let vt = track, let reader = try? AVAssetReader(asset: asset) else { FileHandle.standardError.write("cannot read video\n".data(using: .utf8)!); exit(1) }
// decode small (the long side 960 px) at the stored aspect (undistorted faces); Vision gets the orientation, so it sees
// upright faces and its boxes are in the DISPLAYED frame (2026-10-12: a 180-degree iPhone take came out mirrored
// left-right without this, and every speaker was swapped)
let k = 960.0 / Double(max(natural.width, natural.height))
let out = AVAssetReaderTrackOutput(track: vt, outputSettings: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
                                                                 kCVPixelBufferWidthKey as String: Int((Double(natural.width) * k).rounded()),
                                                                 kCVPixelBufferHeightKey as String: Int((Double(natural.height) * k).rounded())])
out.alwaysCopiesSampleData = false
reader.add(out)
reader.startReading()
FileManager.default.createFile(atPath: a[2], contents: nil)
let fh = FileHandle(forWritingAtPath: a[2])!
var next = 0.0, n = 0
let f2 = { (v: Double) in String(format: "%.4f", v) }
while let sb = out.copyNextSampleBuffer() {
  let t = CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(sb))
  if t + 1e-6 < next { continue }
  next = (Double(Int(t * rate)) + 1) / rate
  guard let px = CMSampleBufferGetImageBuffer(sb) else { continue }
  let req = VNDetectFaceLandmarksRequest()
  req.revision = VNDetectFaceLandmarksRequestRevision3          // revision 3 also estimates pitch (looking down at a phone)
  try? VNImageRequestHandler(cvPixelBuffer: px, orientation: orient, options: [:]).perform([req])
  var faces: [String] = []
  for f in req.results ?? [] {
    let b = f.boundingBox                                      // normalized, bottom-left origin
    var mouth = 0.0
    if let lips = f.landmarks?.innerLips?.normalizedPoints, lips.count >= 4 {
      let ys = lips.map { Double($0.y) }
      mouth = (ys.max()! - ys.min()!)                          // face-relative (0..1 of the face box height)
    }
    let pitch = f.pitch?.doubleValue ?? 0, yaw = f.yaw?.doubleValue ?? 0
    // eye openness (height / width of each eye outline, averaged): lowered lids = looking down (at a phone), since
    // Vision's pitch is often missing
    var eyes = 0.0, ne = 0.0
    for e in [f.landmarks?.leftEye, f.landmarks?.rightEye] {
      if let pts = e?.normalizedPoints, pts.count >= 4 {
        let xs = pts.map { Double($0.x) }, ys = pts.map { Double($0.y) }
        let w = xs.max()! - xs.min()!
        if w > 0 { eyes += (ys.max()! - ys.min()!) / w; ne += 1 }
      }
    }
    if ne > 0 { eyes /= ne }
    faces.append("{\"x\":\(f2(Double(b.minX))),\"y\":\(f2(1 - Double(b.maxY))),\"w\":\(f2(Double(b.width))),\"h\":\(f2(Double(b.height))),\"mouth\":\(f2(mouth)),\"pitch\":\(f2(pitch)),\"yaw\":\(f2(yaw)),\"eyes\":\(f2(eyes))}")
  }
  fh.write("{\"t\":\(f2(t)),\"faces\":[\(faces.joined(separator: ","))]}\n".data(using: .utf8)!)
  n += 1
}
fh.closeFile()
print("{\"samples\":\(n)}")
