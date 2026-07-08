# ponytail: naive line/char clipping, not secret-aware — don't rely on this to hide sensitive output
def clip($n): if length > $n then .[0:$n] + "…" else . end;
def firstlines($n):
  split("\n") as $lines
  | if ($lines | length) > $n
    then ($lines[0:$n] | join("\n")) + "\n  …"
    else . end;

if .type == "assistant" then
  (.message.content // [])[]
  | if .type == "text" then .text
    elif .type == "tool_use" then
      "→ " + .name + ": " + ((.input.command // .input.file_path // .input.pattern // (.input | tostring)) | tostring | clip(200))
    else empty end
elif .type == "user" then
  (.message.content // [])[]?
  | select(.type == "tool_result")
  | ((if (.content | type) == "array" then (.content | map(.text? // (. | tostring)) | join("\n")) else (.content | tostring) end) | firstlines(3)) as $c
  | "  " + $c
elif .type == "result" then
  "── " + (if .is_error then "FAILED" else "done" end) + ": " + (.structured_output.summary // .result // "")
else empty
end
