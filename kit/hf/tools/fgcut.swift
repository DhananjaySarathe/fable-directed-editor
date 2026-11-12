// fgcut: cut the main object(s) out of a still image with Apple Vision's foreground instance mask (on-device, macOS 14+).
// For the paper-collage preset's "hero objects" (kit/presets/paper_collage): a photoreal product shot or a photo becomes a
// transparent PNG cropped to the object, ready to sit on paper with a drop shadow.
//
//   swiftc -O -o kit/bin/fgcut kit/hf/tools/fgcut.swift
//   kit/bin/fgcut <in.jpg|png> <out.png> [pad px, default 24]
//
// Prints a JSON line: {"w":..,"h":..,"instances":n,"cover":share of the frame the object covers}. Exit 2 when Vision finds
// no foreground (use a plainer background, or cut it by hand).
//
//   kit/bin/fgcut <in> <mask.png> --mask[=x,y]     the full-frame alpha mask (8-bit grey, the image's size) of the instance
//                                                  under the point x,y (0..1, top-left origin), or of all instances: for a
//                                                  freeze-frame "sticker" that has to sit exactly where the person is
//                                                  (films/guest-podcast intro cards, 2026-10-12)
import Foundation
import Vision
import CoreImage
import CoreImage.CIFilterBuiltins
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count >= 3 else { FileHandle.standardError.write("usage: fgcut <in> <out.png> [pad]\n".data(using: .utf8)!); exit(1) }
let maskArg = args.first { $0.hasPrefix("--mask") }
let pad = args.count > 3 && maskArg == nil ? CGFloat(Double(args[3]) ?? 24) : 24
let url = URL(fileURLWithPath: args[1])
guard let src = CIImage(contentsOf: url, options: [.applyOrientationProperty: true]) else { FileHandle.standardError.write("cannot read \(args[1])\n".data(using: .utf8)!); exit(1) }

let req = VNGenerateForegroundInstanceMaskRequest()
let handler = VNImageRequestHandler(ciImage: src)
do { try handler.perform([req]) } catch { FileHandle.standardError.write("vision: \(error)\n".data(using: .utf8)!); exit(1) }
guard let obs = req.results?.first, !obs.allInstances.isEmpty else { print("{\"instances\":0}"); exit(2) }
var pick = obs.allInstances
if let m = maskArg, m.contains("=") {
  let xy = m.split(separator: "=")[1].split(separator: ",").compactMap { Double($0) }
  let lab = obs.instanceMask
  CVPixelBufferLockBaseAddress(lab, .readOnly)
  let lw = CVPixelBufferGetWidth(lab), lh = CVPixelBufferGetHeight(lab), rb = CVPixelBufferGetBytesPerRow(lab)
  let base = CVPixelBufferGetBaseAddress(lab)!.assumingMemoryBound(to: UInt8.self)
  // the label under the point, or the nearest labelled pixel within a small radius
  let px = Int(xy[0] * Double(lw)), py = Int(xy[1] * Double(lh))
  var found = 0
  for r in 0..<max(lw, lh) / 6 where found == 0 {
    for dy in -r...r { for dx in -r...r where found == 0 {
      let x = min(max(0, px + dx), lw - 1), y = min(max(0, py + dy), lh - 1)
      let v = Int(base[y * rb + x]); if v > 0 { found = v }
    } }
  }
  CVPixelBufferUnlockBaseAddress(lab, .readOnly)
  if found > 0 { pick = IndexSet(integer: found) }
}
let maskBuf = try obs.generateScaledMaskForImage(forInstances: pick, from: handler)
let mask = CIImage(cvPixelBuffer: maskBuf)
if maskArg != nil {
  let ctx0 = CIContext()
  guard let cgm = ctx0.createCGImage(mask, from: src.extent, format: .L8, colorSpace: CGColorSpaceCreateDeviceGray()) else { exit(1) }
  let d0 = CGImageDestinationCreateWithURL(URL(fileURLWithPath: args[2]) as CFURL, UTType.png.identifier as CFString, 1, nil)!
  CGImageDestinationAddImage(d0, cgm, nil); CGImageDestinationFinalize(d0)
  print("{\"w\":\(Int(src.extent.width)),\"h\":\(Int(src.extent.height)),\"instances\":\(obs.allInstances.count),\"picked\":\(pick.count)}")
  exit(0)
}

// the object on transparency
let blend = CIFilter.blendWithMask()
blend.inputImage = src
blend.backgroundImage = CIImage.empty().cropped(to: src.extent)
blend.maskImage = mask
guard let cut = blend.outputImage else { exit(1) }

// crop to the mask's bounding box (+ pad)
let ctx = CIContext()
let w = Int(src.extent.width), h = Int(src.extent.height)
var data = [UInt8](repeating: 0, count: w * h)
ctx.render(mask, toBitmap: &data, rowBytes: w, bounds: src.extent, format: .L8, colorSpace: nil)
var minX = w, minY = h, maxX = 0, maxY = 0, on = 0
for y in 0..<h { for x in 0..<w where data[y * w + x] > 127 { on += 1; minX = min(minX, x); maxX = max(maxX, x); minY = min(minY, y); maxY = max(maxY, y) } }
if on == 0 { print("{\"instances\":0}"); exit(2) }
// bitmap rows run top-down; CIImage y runs bottom-up
let box = CGRect(x: CGFloat(minX) - pad, y: CGFloat(h - 1 - maxY) - pad, width: CGFloat(maxX - minX + 1) + 2 * pad, height: CGFloat(maxY - minY + 1) + 2 * pad).intersection(src.extent)
let out = cut.cropped(to: box).transformed(by: CGAffineTransform(translationX: -box.minX, y: -box.minY))
guard let cg = ctx.createCGImage(out, from: CGRect(origin: .zero, size: box.size), format: .RGBA8, colorSpace: CGColorSpace(name: CGColorSpace.sRGB)) else { exit(1) }
let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: args[2]) as CFURL, UTType.png.identifier as CFString, 1, nil)!
CGImageDestinationAddImage(dest, cg, nil)
CGImageDestinationFinalize(dest)
print("{\"w\":\(Int(box.width)),\"h\":\(Int(box.height)),\"instances\":\(obs.allInstances.count),\"cover\":\(String(format: "%.3f", Double(on) / Double(w * h)))}")
