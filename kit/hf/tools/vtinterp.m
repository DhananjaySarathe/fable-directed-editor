// vtinterp W H in.rgb out.rgb plan.txt   (build: clang -O2 -fobjc-arc -framework Foundation -framework VideoToolbox -framework CoreVideo -framework CoreMedia vtinterp.m -o kit/bin/vtinterp)
// in.rgb: N frames of rgb24 WxH. plan.txt: one "i phase" per output frame (phase 0 = frame i as is,
// otherwise Apple's ML frame-rate conversion between frame i and i+1). Writes rgb24 frames to out.rgb.
#import <Foundation/Foundation.h>
#import <VideoToolbox/VideoToolbox.h>
#import <CoreMedia/CoreMedia.h>

static CVPixelBufferRef makeBuf(NSDictionary *attrs, int W, int H) {
  CVPixelBufferRef pb = NULL;
  NSMutableDictionary *a = [attrs mutableCopy];
  a[(id)kCVPixelBufferIOSurfacePropertiesKey] = @{};
  CVPixelBufferCreate(kCFAllocatorDefault, W, H, kCVPixelFormatType_64RGBAHalf, (__bridge CFDictionaryRef)a, &pb);
  return pb;
}
static void fill(CVPixelBufferRef pb, const uint8_t *rgb, int W, int H) {
  CVPixelBufferLockBaseAddress(pb, 0);
  uint8_t *base = CVPixelBufferGetBaseAddress(pb); size_t bpr = CVPixelBufferGetBytesPerRow(pb);
  for (int y = 0; y < H; y++) {
    _Float16 *row = (_Float16 *)(base + y * bpr); const uint8_t *s = rgb + (size_t)y * W * 3;
    for (int x = 0; x < W; x++) { row[4*x] = s[3*x] / 255.0f; row[4*x+1] = s[3*x+1] / 255.0f; row[4*x+2] = s[3*x+2] / 255.0f; row[4*x+3] = 1.0f; }
  }
  CVPixelBufferUnlockBaseAddress(pb, 0);
}
static void dump(CVPixelBufferRef pb, uint8_t *rgb, int W, int H) {
  CVPixelBufferLockBaseAddress(pb, kCVPixelBufferLock_ReadOnly);
  uint8_t *base = CVPixelBufferGetBaseAddress(pb); size_t bpr = CVPixelBufferGetBytesPerRow(pb);
  for (int y = 0; y < H; y++) {
    _Float16 *row = (_Float16 *)(base + y * bpr); uint8_t *d = rgb + (size_t)y * W * 3;
    for (int x = 0; x < W; x++) for (int c = 0; c < 3; c++) {
      float v = (float)row[4*x+c] * 255.0f + 0.5f; d[3*x+c] = v < 0 ? 0 : v > 255 ? 255 : (uint8_t)v; }
  }
  CVPixelBufferUnlockBaseAddress(pb, kCVPixelBufferLock_ReadOnly);
}
int main(int argc, char **argv) { @autoreleasepool {
  if (argc < 6) { fprintf(stderr, "usage: vtinterp W H in.rgb out.rgb plan.txt\n"); return 2; }
  int W = atoi(argv[1]), H = atoi(argv[2]); size_t fsz = (size_t)W * H * 3;
  NSData *in = [NSData dataWithContentsOfFile:@(argv[3]) options:NSDataReadingMappedIfSafe error:nil];
  int N = (int)(in.length / fsz); const uint8_t *src = in.bytes;
  NSString *plan = [NSString stringWithContentsOfFile:@(argv[5]) encoding:NSUTF8StringEncoding error:nil];
  FILE *out = fopen(argv[4], "wb");
  VTFrameRateConversionConfiguration *cfg = [[VTFrameRateConversionConfiguration alloc] initWithFrameWidth:W frameHeight:H
      usePrecomputedFlow:NO qualityPrioritization:VTFrameRateConversionConfigurationQualityPrioritizationQuality
      revision:VTFrameRateConversionConfiguration.defaultRevision];
  VTFrameProcessor *proc = [[VTFrameProcessor alloc] init];
  NSError *err = nil;
  if (![proc startSessionWithConfiguration:cfg error:&err]) { fprintf(stderr, "session: %s\n", err.description.UTF8String); return 1; }
  CVPixelBufferRef a = makeBuf(cfg.sourcePixelBufferAttributes, W, H), b = makeBuf(cfg.sourcePixelBufferAttributes, W, H);
  CVPixelBufferRef d = makeBuf(cfg.destinationPixelBufferAttributes, W, H);
  uint8_t *tmp = malloc(fsz); int loaded = -1, written = 0;
  for (NSString *line in [plan componentsSeparatedByString:@"\n"]) {
    NSArray *p = [line componentsSeparatedByString:@" "]; if (p.count < 2) continue;
    int i = [p[0] intValue]; float ph = [p[1] floatValue];
    if (i >= N - 1) { i = N - 1; ph = 0; }
    if (ph <= 0.0005f) { fwrite(src + (size_t)i * fsz, 1, fsz, out); written++; continue; }
    if (loaded != i) { fill(a, src + (size_t)i * fsz, W, H); fill(b, src + (size_t)(i + 1) * fsz, W, H); loaded = i; }
    VTFrameProcessorFrame *fa = [[VTFrameProcessorFrame alloc] initWithBuffer:a presentationTimeStamp:CMTimeMake(i, 60)];
    VTFrameProcessorFrame *fb = [[VTFrameProcessorFrame alloc] initWithBuffer:b presentationTimeStamp:CMTimeMake(i + 1, 60)];
    VTFrameProcessorFrame *fd = [[VTFrameProcessorFrame alloc] initWithBuffer:d presentationTimeStamp:CMTimeMake((int64_t)((i + ph) * 1000), 60000)];
    VTFrameRateConversionParameters *prm = [[VTFrameRateConversionParameters alloc] initWithSourceFrame:fa nextFrame:fb opticalFlow:nil
        interpolationPhase:@[@(ph)] submissionMode:VTFrameRateConversionParametersSubmissionModeRandom destinationFrames:@[fd]];
    if (![proc processWithParameters:prm error:&err]) { fprintf(stderr, "process %d %.3f: %s\n", i, ph, err.description.UTF8String); return 1; }
    dump(d, tmp, W, H); fwrite(tmp, 1, fsz, out); written++;
  }
  [proc endSession]; fclose(out);
  fprintf(stderr, "wrote %d frames from %d\n", written, N);
}}
