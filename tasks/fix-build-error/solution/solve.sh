#!/bin/bash
cd /project
cat > app/page.tsx << 'EOF'
"use client";
import { useState } from "react";

export default function Home() {
  const [count, setCount] = useState(0);
  const items: string[] = ["1", "2", "3"];

  return (
    <main className="min-h-screen flex flex-col items-center justify-center">
      <h1 className="text-4xl font-bold">Welcome</h1>
      <p>Count: {count}</p>
      <div>
        {items.map((item, i) => (
          <span key={i}>{item}</span>
        ))}
      </div>
      <button onClick={() => setCount(count + 1)}>Increment</button>
    </main>
  );
}
EOF
npm run build
