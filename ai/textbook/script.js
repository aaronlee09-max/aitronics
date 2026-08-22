const slides = Array.from(document.querySelectorAll(".slide"));
const prevButton = document.querySelector(".nav-prev");
const nextButton = document.querySelector(".nav-next");
const currentSlide = document.querySelector("#currentSlide");
const totalSlides = document.querySelector("#totalSlides");
const dots = document.querySelector(".dots");
const deck = document.querySelector(".deck");
const DESIGN_WIDTH = 1920;
const DESIGN_HEIGHT = 1080;
function fitDeckToViewport() {
  const scale = Math.min(window.innerWidth / DESIGN_WIDTH, window.innerHeight / DESIGN_HEIGHT);
  deck.style.setProperty("--deck-scale", String(scale));
}
window.addEventListener("resize", fitDeckToViewport);
fitDeckToViewport();
let activeIndex = 0;
slides.forEach((_, index) => {
  const dot = document.createElement("button");
  dot.className = "dot";
  dot.type = "button";
  dot.setAttribute("aria-label", `${index + 1}번 슬라이드로 이동`);
  dot.addEventListener("click", () => showSlide(index));
  dots.append(dot);
});
const dotButtons = Array.from(document.querySelectorAll(".dot"));
totalSlides.textContent = String(slides.length);
function showSlide(index) {
  activeIndex = (index + slides.length) % slides.length;
  slides.forEach((slide, slideIndex) => slide.classList.toggle("active", slideIndex === activeIndex));
  dotButtons.forEach((dot, dotIndex) => dot.classList.toggle("active", dotIndex === activeIndex));
  currentSlide.textContent = String(activeIndex + 1);
}
function nextSlide() { showSlide(activeIndex + 1); }
function prevSlide() { showSlide(activeIndex - 1); }
prevButton.addEventListener("click", prevSlide);
nextButton.addEventListener("click", nextSlide);
document.addEventListener("keydown", (event) => {
  if (event.target.matches("input, textarea, button, a")) return;
  if (event.key === "ArrowRight" || event.key === " ") { event.preventDefault(); nextSlide(); }
  if (event.key === "ArrowLeft") prevSlide();
});
document.querySelectorAll("[data-choice]").forEach((button) => {
  button.addEventListener("click", () => {
    const group = button.closest(".quiz");
    if (!group) return;
    group.querySelectorAll("[data-choice]").forEach((item) => item.classList.remove("picked", "correct", "wrong"));
    button.classList.add("picked");
    button.classList.add(button.dataset.choice === "ok" ? "correct" : "wrong");
    const result = group.querySelector(".quiz-result");
    if (result) result.textContent = button.dataset.msg || "";
  });
});
document.querySelectorAll("[data-tab]").forEach((button) => {
  button.addEventListener("click", () => {
    const wrap = button.closest(".tab-box");
    wrap.querySelectorAll("[data-tab]").forEach((item) => item.classList.toggle("active", item === button));
    wrap.querySelectorAll("[data-panel]").forEach((panel) => {
      panel.classList.toggle("active", panel.dataset.panel === button.dataset.tab);
    });
  });
});
const requestedSlide = Number(new URLSearchParams(window.location.search).get("slide"));
showSlide(Number.isInteger(requestedSlide) && requestedSlide > 0 ? requestedSlide - 1 : 0);
