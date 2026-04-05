FROM autoagent-base

RUN cp -r /template/project /project
WORKDIR /project

# Introduce deliberate build errors
RUN cat > app/page.tsx << 'BROKEN'
import { useState } from "react";
import { MissingComponent } from "@/components/missing";

export default function Home() {
  const [count, setCount] = useState(0);
  const items: string[] = [1, 2, 3]; // type error

  return (
    <main className="min-h-screen flex flex-col items-center justify-center">
      <h1 className="text-4xl font-bold">Welcome</h1>
      <MissingComponent />
      <p>Count: {count}</p>
      <div>
        {items.map(item => (
          <span>{item}</span>
        ))}
      </div>
      <button onClick={() => setCount(count + 1)}>
        Increment
      </button>
    </main>
  );
}
BROKEN
