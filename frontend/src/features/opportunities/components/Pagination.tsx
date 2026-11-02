interface Props {
  page: number;
  total: number;
  limit: number;
  onChange: (page: number) => void;
}

export default function Pagination({ page, total, limit, onChange }: Props) {
  const pages = Math.ceil(total / limit);
  if (pages <= 1) return null;
  return (
    <nav className="pagination">
      <button disabled={page <= 1} onClick={() => onChange(page - 1)}>Previous</button>
      {Array.from({ length: pages }, (_, i) => i + 1).map((p) => (
        <button key={p} className={p === page ? "active" : ""} onClick={() => onChange(p)}>
          {p}
        </button>
      ))}
      <button disabled={page >= pages} onClick={() => onChange(page + 1)}>Next</button>
    </nav>
  );
}
