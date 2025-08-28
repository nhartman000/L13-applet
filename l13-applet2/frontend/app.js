let startTime = Date.now(), paused = false;

function updateTimer() {
  if (!paused) {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    document.getElementById("timer").innerText = `⏱️ Elapsed: ${elapsed}s`;
  }
}
setInterval(updateTimer, 1000);

function pause() { paused = true; }
function resume() { paused = false; }

function sendPrompt() {
  const input = document.getElementById("userInput").value;
  fetch("/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ seed: { prompt: input } })
  })
  .then(res => res.json())
  .then(data => {
    document.getElementById("responses").innerHTML = data.history.map(h =>
      `<div><strong>Pass ${h.pass_id}:</strong> ${JSON.stringify(h.data)}</div>`
    ).join("");
  });
}
