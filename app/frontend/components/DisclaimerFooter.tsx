export default function DisclaimerFooter() {
  return (
    <div className="mt-10 rounded-2xl border border-white/[0.08] bg-black/25 p-5 text-xs leading-relaxed text-zinc-400 backdrop-blur">
      <p>
        This is a 4.0-scale relative application-strength index, not an
        admission probability. Missing or blocked sources widen the confidence
        band instead of being guessed.
      </p>
      <p className="mt-2 text-zinc-500">
        这是一个 4.0 制的相对申请强度指数，不是录取概率。证据无法验证或来源被拦截时，confidence
        band 会变宽，而不是被猜测填充。
      </p>
    </div>
  );
}
