const revealItems = document.querySelectorAll(".reveal");
const metricValues = document.querySelectorAll("[data-count]");
const processSteps = document.querySelectorAll(".process-step");
const processPanels = document.querySelectorAll(".process-panel");
const scenarioTabs = document.querySelectorAll(".scenario-tab");
const scenarioPanels = document.querySelectorAll(".scenario-panel");
const navLinks = document.querySelectorAll(".site-nav a");
const sections = document.querySelectorAll("main section[id]");

const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("visible");
        revealObserver.unobserve(entry.target);
    });
}, { threshold: 0.18 });

revealItems.forEach((item) => revealObserver.observe(item));

const metricObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
        if (!entry.isIntersecting) return;

        const el = entry.target;
        const target = Number(el.dataset.count || "0");
        const duration = 1100;
        const start = performance.now();

        const update = (now) => {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.round(target * eased).toString();
            if (progress < 1) requestAnimationFrame(update);
        };

        requestAnimationFrame(update);
        metricObserver.unobserve(el);
    });
}, { threshold: 0.55 });

metricValues.forEach((item) => metricObserver.observe(item));

processSteps.forEach((step) => {
    step.addEventListener("click", () => {
        const stage = step.dataset.stage;

        processSteps.forEach((button) => {
            const active = button.dataset.stage === stage;
            button.classList.toggle("active", active);
            button.setAttribute("aria-selected", active ? "true" : "false");
        });

        processPanels.forEach((panel) => {
            const active = panel.dataset.panel === stage;
            panel.classList.toggle("active", active);
            panel.hidden = !active;
        });
    });
});

scenarioTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
        const target = tab.dataset.tab;

        scenarioTabs.forEach((button) => {
            const active = button.dataset.tab === target;
            button.classList.toggle("active", active);
            button.setAttribute("aria-selected", active ? "true" : "false");
        });

        scenarioPanels.forEach((panel) => {
            const active = panel.dataset.scenario === target;
            panel.classList.toggle("active", active);
            panel.hidden = !active;
        });
    });
});

const setActiveNav = () => {
    let currentId = "";

    sections.forEach((section) => {
        const top = section.getBoundingClientRect().top;
        if (top <= 140) currentId = section.id;
    });

    navLinks.forEach((link) => {
        const active = link.getAttribute("href") === `#${currentId}`;
        link.classList.toggle("active", active);
    });
};

window.addEventListener("scroll", setActiveNav, { passive: true });
setActiveNav();
