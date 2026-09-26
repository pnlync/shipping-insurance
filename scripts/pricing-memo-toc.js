const pricingTocLinks = document.querySelectorAll(".executive-toc a[href^='#']");
const pricingSections = [...pricingTocLinks]
  .map((link) => document.querySelector(link.getAttribute("href")))
  .filter(Boolean);

if (pricingTocLinks.length && pricingSections.length) {
  const setActiveTocLink = () => {
    let activeSection = pricingSections[0];

    pricingSections.forEach((section) => {
      if (section.getBoundingClientRect().top <= 160) {
        activeSection = section;
      }
    });

    pricingTocLinks.forEach((link) => {
      link.classList.toggle("is-active", link.getAttribute("href") === `#${activeSection.id}`);
    });
  };

  setActiveTocLink();
  window.addEventListener("scroll", setActiveTocLink, { passive: true });
}
