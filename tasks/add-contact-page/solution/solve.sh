#!/bin/bash
cd /project
mkdir -p app/contact
cat > app/contact/page.tsx << 'EOF'
export default function Contact() {
  return (
    <main className="min-h-screen bg-white py-16 px-4">
      <div className="max-w-xl mx-auto">
        <h1 className="text-4xl font-bold mb-8">Get in Touch</h1>
        <form className="space-y-4">
          <input type="text" placeholder="Name" className="w-full p-3 border rounded-lg" />
          <input type="email" placeholder="Email" className="w-full p-3 border rounded-lg" />
          <input type="tel" placeholder="Phone" className="w-full p-3 border rounded-lg" />
          <textarea placeholder="Message" rows={5} className="w-full p-3 border rounded-lg" />
          <button type="submit" className="w-full p-3 bg-blue-600 text-white font-bold rounded-lg">Send</button>
        </form>
        <div className="mt-8 text-gray-600">
          <p>Acme Corp</p>
          <p>123 Business Ave, New York, NY 10001</p>
          <p>Email: contact@acme.com</p>
          <p>Phone: (555) 123-4567</p>
        </div>
      </div>
    </main>
  );
}
EOF
npm run build
