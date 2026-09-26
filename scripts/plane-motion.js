const planes = document.querySelectorAll(".risk-plane, .memo-plane");

if (planes.length && window.matchMedia("(prefers-reduced-motion: no-preference)").matches) {
  planes.forEach((plane) => {
  plane.addEventListener("pointermove", (event) => {
    const rect = plane.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width - 0.5;
    const y = (event.clientY - rect.top) / rect.height - 0.5;
    plane.style.setProperty("--tilt-x", `${x * 8}px`);
    plane.style.setProperty("--tilt-y", `${y * 8}px`);
    plane.querySelectorAll(".flow-node, .formula-stack > div").forEach((node, index) => {
      const depth = (index + 1) * 0.18;
      node.style.transform = `translate3d(${x * depth * 18}px, ${y * depth * 18}px, 0)`;
    });
  });

  plane.addEventListener("pointerleave", () => {
    plane.querySelectorAll(".flow-node, .formula-stack > div").forEach((node) => {
      node.style.transform = "translate3d(0, 0, 0)";
    });
  });
  });
}
