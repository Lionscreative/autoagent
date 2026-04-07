#!/bin/bash
# Reference solution — DailyStreak habit tracker
cd /project

cat > app/page.tsx << 'EOF'
"use client";
import { useState, useEffect } from "react";

type Habit = { id: string; name: string; completed: Record<string, boolean> };

export default function Home() {
  const [habits, setHabits] = useState<Habit[]>([]);
  const [name, setName] = useState("");

  useEffect(() => {
    const saved = localStorage.getItem("dailystreak-habits");
    if (saved) setHabits(JSON.parse(saved));
  }, []);

  useEffect(() => {
    localStorage.setItem("dailystreak-habits", JSON.stringify(habits));
  }, [habits]);

  const addHabit = () => {
    if (!name.trim()) return;
    setHabits([...habits, { id: crypto.randomUUID(), name, completed: {} }]);
    setName("");
  };

  const toggle = (id: string, day: string) => {
    setHabits(habits.map(h => h.id === id ? { ...h, completed: { ...h.completed, [day]: !h.completed[day] } } : h));
  };

  const days = Array.from({ length: 30 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (29 - i));
    return d.toISOString().slice(0, 10);
  });

  return (
    <main className="min-h-screen bg-neutral-950 text-white p-8">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-5xl font-bold mb-2 text-green-400">DailyStreak</h1>
        <p className="text-neutral-400 mb-8">Track your habits, build your streak.</p>

        <div className="flex gap-2 mb-8">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="New habit..."
            className="flex-1 bg-neutral-900 border border-neutral-800 rounded-lg px-4 py-2 text-white"
          />
          <button onClick={addHabit} className="bg-green-500 hover:bg-green-600 text-black font-bold px-6 rounded-lg">
            Add
          </button>
        </div>

        <div className="space-y-6">
          {habits.map((h) => (
            <div key={h.id} className="bg-neutral-900 rounded-lg p-4 border border-neutral-800">
              <h3 className="font-bold mb-3">{h.name}</h3>
              <div className="grid grid-cols-30 gap-1" style={{ gridTemplateColumns: "repeat(30, 1fr)" }}>
                {days.map((d) => (
                  <button
                    key={d}
                    onClick={() => toggle(h.id, d)}
                    className={`aspect-square rounded ${h.completed[d] ? "bg-green-500" : "bg-neutral-800 hover:bg-neutral-700"}`}
                    title={d}
                  />
                ))}
              </div>
            </div>
          ))}
          {habits.length === 0 && <p className="text-neutral-500 text-center py-12">No habits yet. Add one above.</p>}
        </div>
      </div>
    </main>
  );
}
EOF

npm run build
