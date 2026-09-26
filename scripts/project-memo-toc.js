const executiveTocLinks = document.querySelectorAll(".executive-toc a[href^='#']");
const executiveSections = [...executiveTocLinks]
  .map((link) => document.querySelector(link.getAttribute("href")))
  .filter(Boolean);

if (executiveTocLinks.length && executiveSections.length) {
  const setActiveTocLink = () => {
    let activeSection = executiveSections[0];

    executiveSections.forEach((section) => {
      if (section.getBoundingClientRect().top <= 160) {
        activeSection = section;
      }
    });

    executiveTocLinks.forEach((link) => {
      link.classList.toggle("is-active", link.getAttribute("href") === `#${activeSection.id}`);
    });
  };

  setActiveTocLink();
  window.addEventListener("scroll", setActiveTocLink, { passive: true });
}
