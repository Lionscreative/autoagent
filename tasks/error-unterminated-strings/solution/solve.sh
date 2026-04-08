#!/bin/bash
cd /project
cat > app/page.tsx << 'EOF'
const testimonials = [
  { quote: "Best service I&apos;ve ever had — it&apos;s truly amazing!", name: "Jane Doe", role: "CEO" },
  { quote: 'They said &quot;wow&quot; when they saw the results', name: "John Smith", role: "CTO" },
  { quote: "I can&apos;t believe how fast it was.", name: "Alice", role: "Designer" },
  { quote: "Absolutely &quot;next level&quot; work.", name: "Bob", role: "PM" },
  { quote: "Would recommend to anyone who&apos;s serious.", name: "Eve", role: "Founder" },
];
export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 py-16 px-4">
      <h1 className="text-4xl font-bold text-center mb-12">Testimonials</h1>
      <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
        {testimonials.map((t, i) => (
          <div key={i} className="bg-white rounded-xl p-6 shadow testimonial">
            <p className="quote italic mb-4" dangerouslySetInnerHTML={{__html: t.quote}} />
            <p className="font-semibold">{t.name}</p>
            <p className="role text-sm text-gray-500">{t.role}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
EOF
npm run build
