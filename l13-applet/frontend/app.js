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
  fetch("/multi-agent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt: input })
  })
  .then(res => res.json())
  .then(data => {
    document.querySelector("#agentA span").innerText = data.agent_a.response;
    document.querySelector("#agentB span").innerText = data.agent_b.response;
    document.querySelector("#kernel span").innerText = data.kernel.decision + "\n" +
      data.kernel.emoji_thread.join(" → ");
  });
}
