export default function PageHeader({
  eyebrow,
  title,
  children,
  aside,
}: {
  eyebrow: string;
  title: React.ReactNode;
  children?: React.ReactNode;
  aside?: React.ReactNode;
}) {
  return (
    <div className="animate-fade-up flex flex-wrap items-end justify-between gap-6">
      <div className="max-w-2xl">
        <p className="eyebrow">{eyebrow}</p>
        <h1 className="mt-2.5 text-3xl font-semibold tracking-tight text-white sm:text-[2.6rem] sm:leading-[1.1]">
          {title}
        </h1>
        {children && (
          <p className="mt-3 text-[0.95rem] leading-relaxed text-zinc-400">{children}</p>
        )}
      </div>
      {aside}
    </div>
  );
}
