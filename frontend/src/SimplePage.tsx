export default function SimplePage({ title, text }: { title: string; text: string }) {
  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: "60px 24px" }}>
      <h1>{title}</h1>
      <p style={{ color: "#666" }}>{text}</p>
    </div>
  );
}