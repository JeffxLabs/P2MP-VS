// Mean RGB of rectangles in an image (pixel coords, origin top-left).
// Usage: pixel_probe <image> x,y,w,h [x,y,w,h ...]   -> one "r g b" line per rect
import Foundation
import AppKit

let args = CommandLine.arguments
guard args.count > 2, let img = NSImage(contentsOfFile: args[1]),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    fputs("Usage: pixel_probe <image> x,y,w,h ...\n", stderr); exit(1)
}
let w = cg.width, h = cg.height
var buf = [UInt8](repeating: 0, count: w * h * 4)
let ctx = CGContext(data: &buf, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4,
                    space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
ctx.draw(cg, in: CGRect(x: 0, y: 0, width: w, height: h))
for spec in args.dropFirst(2) {
    let p = spec.split(separator: ",").compactMap { Int($0) }
    guard p.count == 4 else { print("0 0 0"); continue }
    var r = 0, g = 0, b = 0, n = 0
    for y in max(0, p[1])..<min(h, p[1] + p[3]) {
        for x in max(0, p[0])..<min(w, p[0] + p[2]) {
            let i = (y * w + x) * 4
            r += Int(buf[i]); g += Int(buf[i + 1]); b += Int(buf[i + 2]); n += 1
        }
    }
    n = max(n, 1)
    print("\(r / n) \(g / n) \(b / n)")
}
