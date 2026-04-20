export default function Placeholder({ title }: { title: string }) {
  return (
    <div className="p-8 max-w-7xl mx-auto w-full">
      <div
        className="neomorph-raised p-12 rounded-2xl flex flex-col items-center justify-center text-center"
        style={{ backgroundColor: "#e8eaf0", minHeight: 300 }}
      >
        <span className="material-symbols-outlined text-[48px] mb-4" style={{ color: "#6366f1" }}>
          construction
        </span>
        <h2 className="text-xl font-semibold mb-2" style={{ color: "#2e3040" }}>{title}</h2>
        <p className="text-sm" style={{ color: "#585a68" }}>This page is coming soon.</p>
      </div>
    </div>
  );
}
