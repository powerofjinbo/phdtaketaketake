export default function DisclaimerFooter() {
  return (
    <div className="glass-strong mt-10 rounded-xl border-indigo-400/25 p-5 text-sm leading-relaxed text-zinc-200">
      This is a 4.0-scale relative application-strength index, not an admission
      probability. Missing or blocked sources widen the confidence band instead
      of being guessed.
      这是一个 4.0 制的相对申请强度指数，不是录取概率。证据无法验证或来源被拦截时，confidence
      band 会变宽，而不是被猜测填充。
    </div>
  );
}
