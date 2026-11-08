interface Props {
  value: string;
  onChange: (value: string) => void;
}

export default function SearchBar({ value, onChange }: Props) {
  return (
    <input
      className="search"
      type="search"
      placeholder="Search by title, company or skill..."
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
