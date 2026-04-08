#!/bin/bash
cd /project
cat > app/icon.tsx << 'EOF'
import { ImageResponse } from "next/og";
export const size = { width: 32, height: 32 };
export const contentType = "image/png";
export default function Icon() {
  return new ImageResponse(
    (<div style={{ fontSize: 24, background: "linear-gradient(135deg,#0a1a3c,#1e3a8a)", width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 700 }}>N</div>),
    { ...size }
  );
}
EOF
cat > app/apple-icon.tsx << 'EOF'
import { ImageResponse } from "next/og";
export const size = { width: 180, height: 180 };
export const contentType = "image/png";
export default function AppleIcon() {
  return new ImageResponse(
    (<div style={{ fontSize: 120, background: "linear-gradient(135deg,#0a1a3c,#1e3a8a)", width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 700 }}>N</div>),
    { ...size }
  );
}
EOF
cat > app/page.tsx << 'EOF'
export const metadata = { title: "NorthPeak Ventures", description: "Venture capital for bold founders" };
export default function Home() {
  return <main className="min-h-screen bg-slate-950 text-white flex items-center justify-center"><h1 className="text-6xl font-bold">NorthPeak Ventures</h1></main>;
}
EOF
npm run build
