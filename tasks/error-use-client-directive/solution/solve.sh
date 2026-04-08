#!/bin/bash
cd /project
mkdir -p components
cat > components/quiz.tsx << 'EOF'
"use client";
import { useState, useEffect } from "react";
const questions = [
  { q: "2+2?", a: "4" },
  { q: "Capital of France?", a: "Paris" },
  { q: "Sky color?", a: "blue" },
  { q: "H2O?", a: "water" },
  { q: "Largest planet?", a: "Jupiter" },
];
export default function Quiz() {
  const [i, setI] = useState(0);
  const [score, setScore] = useState(0);
  const [time, setTime] = useState(30);
  useEffect(() => {
    const t = setInterval(() => setTime(x => Math.max(0, x - 1)), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="p-8 bg-white rounded-xl shadow max-w-md mx-auto">
      <p className="text-sm text-gray-500">Time: {time}s | Score: {score}</p>
      <h2 className="text-2xl font-bold my-4">{questions[i]?.q}</h2>
      <button className="px-4 py-2 bg-blue-600 text-white rounded" onClick={() => { setScore(s => s + 1); setI(x => (x + 1) % 5); }}>Next</button>
    </div>
  );
}
EOF
cat > app/page.tsx << 'EOF'
import Quiz from "@/components/quiz";
export default function Home() {
  return <main className="min-h-screen bg-gray-50 py-16"><Quiz /></main>;
}
EOF
npm run build
