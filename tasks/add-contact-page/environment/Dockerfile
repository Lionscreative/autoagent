FROM autoagent-base

RUN cp -r /template/project /project
WORKDIR /project

# Create a pre-existing homepage that should NOT be modified
RUN cat > app/page.tsx << 'EXISTING'
export default function Home() {
  return (
    <main className="min-h-screen bg-white">
      <section className="flex flex-col items-center justify-center min-h-[60vh] px-4">
        <h1 className="text-5xl font-bold text-blue-600">Acme Corp</h1>
        <p className="text-xl text-gray-600 mt-4">Building the future, one product at a time.</p>
        <div className="mt-8 flex gap-4">
          <a href="/contact" className="px-6 py-3 bg-blue-600 text-white rounded-lg">Contact Us</a>
        </div>
      </section>
      <section className="max-w-4xl mx-auto py-16 px-4">
        <h2 className="text-3xl font-bold mb-8 text-center">Our Services</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="p-6 border rounded-lg">
            <h3 className="text-xl font-bold mb-2">Consulting</h3>
            <p className="text-gray-600">Expert advice for your business needs.</p>
          </div>
          <div className="p-6 border rounded-lg">
            <h3 className="text-xl font-bold mb-2">Development</h3>
            <p className="text-gray-600">Custom software solutions.</p>
          </div>
          <div className="p-6 border rounded-lg">
            <h3 className="text-xl font-bold mb-2">Design</h3>
            <p className="text-gray-600">Beautiful, user-friendly interfaces.</p>
          </div>
        </div>
      </section>
    </main>
  );
}
EXISTING

# Save a hash to verify it wasn't modified
RUN md5sum app/page.tsx > /tmp/homepage_hash.txt
