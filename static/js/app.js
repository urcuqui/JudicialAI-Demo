(() => {
  "use strict";

  const STRUCTURED_FIELDS = [
    { key: "facts", label: "Hechos relevantes" },
    { key: "dates", label: "Fechas" },
    { key: "actors", label: "Actores" },
    { key: "prosecution_arguments", label: "Argumentos de la fiscalía" },
    { key: "defense_arguments", label: "Argumentos de la defensa" },
    { key: "evidence", label: "Evidencia" },
    { key: "contradictions", label: "Contradicciones" },
    { key: "unverified_information", label: "Información no verificada" },
  ];

  const AUDIENCE_SCENARIOS = [
    {
      text: "Resumir una resolución pública.",
      classification: "verde",
      explanation:
        "Resumir un documento ya público es una tarea de organización de información, no de decisión. Uso apropiado con revisión editorial mínima.",
    },
    {
      text: "Organizar argumentos presentados por fiscalía y defensa.",
      classification: "verde",
      explanation:
        "Clasificar y estructurar argumentos ya existentes facilita la revisión humana sin sustituir el juicio jurídico.",
    },
    {
      text: "Preparar un borrador administrativo.",
      classification: "verde",
      explanation:
        "Generar un borrador administrativo que luego será revisado por una persona es un uso apropiado de asistencia documental.",
    },
    {
      text: "Subir un expediente confidencial a una herramienta pública de IA.",
      classification: "rojo",
      explanation:
        "Cargar información confidencial en una herramienta pública de IA compromete la confidencialidad y la cadena de custodia de la información. No debe hacerse.",
    },
    {
      text: "Pedir a la IA que determine qué testigo está diciendo la verdad.",
      classification: "rojo",
      explanation:
        "Evaluar la credibilidad de un testimonio es una función judicial esencial que no puede delegarse a un sistema de IA.",
    },
    {
      text: "Comparar dos documentos para identificar contradicciones que después revisará el juez.",
      classification: "verde",
      explanation:
        "Detectar posibles contradicciones para que un humano las revise es asistencia, no decisión: la IA señala, la persona evalúa.",
    },
    {
      text: "Pedir a la IA que determine la probabilidad de reincidencia de una persona.",
      classification: "rojo",
      explanation:
        "Predecir el comportamiento criminal individual de una persona es una forma de decisión automatizada de alto riesgo que no debe delegarse.",
    },
    {
      text: "Generar alternativas de redacción que después serán revisadas por un funcionario.",
      classification: "amarillo",
      explanation:
        "Generar texto que influye en un documento judicial requiere controles adicionales: revisión humana obligatoria y trazabilidad del origen del texto.",
    },
  ];

  const CLASSIFICATION_META = {
    verde: { label: "🟢 Recomendado", className: "callout--safe" },
    amarillo: { label: "🟡 Requiere controles adicionales", className: "callout--warning" },
    rojo: { label: "🔴 No delegar", className: "callout--danger" },
  };

  let caseData = null;
  let audienceIndex = 0;
  let audienceVoted = false;

  const $ = (id) => document.getElementById(id);

  async function postJSON(url) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    let data;
    try {
      data = await response.json();
    } catch (err) {
      throw new Error("El servidor devolvió una respuesta inválida.");
    }
    if (!response.ok) {
      throw new Error(data.error || "Ocurrió un error al consultar la IA.");
    }
    return data;
  }

  function show(el) { el.hidden = false; }
  function hide(el) { el.hidden = true; }

  function renderStructured(container, data) {
    container.innerHTML = "";
    STRUCTURED_FIELDS.forEach(({ key, label }) => {
      const items = Array.isArray(data[key]) ? data[key] : [];
      const field = document.createElement("div");
      field.className = "structured-field" + (items.length === 0 ? " structured-field--empty" : "") +
        (key === "contradictions" || key === "unverified_information" ? ` structured-field--${key}` : "");

      const heading = document.createElement("h4");
      heading.textContent = label;
      field.appendChild(heading);

      const list = document.createElement("ul");
      if (items.length === 0) {
        const li = document.createElement("li");
        li.textContent = "Sin elementos identificados.";
        list.appendChild(li);
      } else {
        items.forEach((item) => {
          const li = document.createElement("li");
          li.textContent = item;
          list.appendChild(li);
        });
      }
      field.appendChild(list);
      container.appendChild(field);
    });
  }

  // -------------------------------------------------------------------
  // Carga del expediente
  // -------------------------------------------------------------------

  async function loadCase() {
    try {
      const response = await fetch("/api/case");
      caseData = await response.json();
      $("case-document").textContent = caseData.document;
      renderScenario3Document();
    } catch (err) {
      $("case-document").textContent = "No se pudo cargar el expediente.";
    }
  }

  function renderScenario3Document() {
    if (!caseData) return;
    const preview = $("document-preview");
    const full = $("document-full");

    const previewText = caseData.document_with_injection
      .split("\n")
      .slice(0, 12)
      .join("\n") + "\n\n[... documento truncado — active \"Mostrar documento completo\" para verlo íntegro ...]";
    preview.textContent = previewText;

    full.innerHTML = "";
    const parts = caseData.document_with_injection.split(caseData.hidden_instruction);
    parts.forEach((part, index) => {
      full.appendChild(document.createTextNode(part));
      if (index < parts.length - 1) {
        const mark = document.createElement("span");
        mark.className = "injection-highlight";
        mark.textContent = caseData.hidden_instruction;
        full.appendChild(mark);
      }
    });
  }

  // -------------------------------------------------------------------
  // Escenario 1 — Delegación peligrosa
  // -------------------------------------------------------------------

  function initScenario1() {
    const btn = $("btn-dangerous");
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      hide($("error-dangerous"));
      hide($("result-dangerous"));
      hide($("explain-dangerous"));
      show($("loading-dangerous"));
      try {
        const data = await postJSON("/api/analyze/dangerous");
        $("result-dangerous-content").textContent = data.response;
        show($("result-dangerous"));
        show($("explain-dangerous"));
      } catch (err) {
        $("error-dangerous").textContent = err.message;
        show($("error-dangerous"));
      } finally {
        hide($("loading-dangerous"));
        btn.disabled = false;
      }
    });
  }

  // -------------------------------------------------------------------
  // Escenario 2 — Asistencia responsable
  // -------------------------------------------------------------------

  function initScenario2() {
    const btn = $("btn-responsible");
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      hide($("error-responsible"));
      hide($("result-responsible"));
      hide($("explain-responsible"));
      show($("loading-responsible"));
      try {
        const data = await postJSON("/api/analyze/responsible");
        const content = $("result-responsible-content");
        if (data.structured) {
          renderStructured(content, data.data);
        } else {
          content.innerHTML = "";
          const pre = document.createElement("div");
          pre.className = "model-response";
          pre.textContent = data.raw;
          content.appendChild(pre);
        }
        show($("result-responsible"));
        show($("explain-responsible"));
      } catch (err) {
        $("error-responsible").textContent = err.message;
        show($("error-responsible"));
      } finally {
        hide($("loading-responsible"));
        btn.disabled = false;
      }
    });
  }

  // -------------------------------------------------------------------
  // Escenario 3 — Prompt injection indirecto
  // -------------------------------------------------------------------

  function initScenario3() {
    const toggle = $("toggle-full-document");
    toggle.addEventListener("change", () => {
      if (toggle.checked) {
        hide($("document-preview"));
        show($("document-full"));
      } else {
        show($("document-preview"));
        hide($("document-full"));
      }
    });

    $("btn-injection").addEventListener("click", async () => {
      const btn = $("btn-injection");
      btn.disabled = true;
      hide($("error-injection"));
      hide($("result-injection"));
      show($("loading-injection"));
      try {
        const data = await postJSON("/api/analyze/injection");
        $("result-injection-content").textContent = data.response;
        show($("result-injection"));
        show($("explain-injection"));
      } catch (err) {
        $("error-injection").textContent = err.message;
        show($("error-injection"));
      } finally {
        hide($("loading-injection"));
        btn.disabled = false;
      }
    });

    $("btn-protected").addEventListener("click", async () => {
      const btn = $("btn-protected");
      btn.disabled = true;
      hide($("error-protected"));
      hide($("result-protected"));
      show($("loading-protected"));
      try {
        const data = await postJSON("/api/analyze/protected");
        const banner = $("detection-banner");
        const content = $("result-protected-content");

        if (data.structured) {
          const suspicious = data.data.suspicious_instructions_detected || [];
          if (data.data.document_integrity_warning || suspicious.length > 0) {
            banner.className = "detection-banner detection-banner--alert";
            let text = "⚠ Se detectó una instrucción sospechosa dentro del documento.";
            if (suspicious.length > 0) {
              text += " " + suspicious.join(" | ");
            }
            banner.textContent = text;
          } else {
            banner.className = "detection-banner detection-banner--clear";
            banner.textContent = "No se reportaron instrucciones sospechosas.";
          }
          show(banner);
          renderStructured(content, data.data.analysis);
        } else {
          hide(banner);
          content.innerHTML = "";
          const pre = document.createElement("div");
          pre.className = "model-response";
          pre.textContent = data.raw;
          content.appendChild(pre);
        }
        show($("result-protected"));
        show($("explain-injection"));
      } catch (err) {
        $("error-protected").textContent = err.message;
        show($("error-protected"));
      } finally {
        hide($("loading-protected"));
        btn.disabled = false;
      }
    });
  }

  // -------------------------------------------------------------------
  // Componente interactivo de audiencia
  // -------------------------------------------------------------------

  function renderAudienceScenario() {
    const scenario = AUDIENCE_SCENARIOS[audienceIndex];
    $("audience-progress-label").textContent =
      `Escenario ${audienceIndex + 1} de ${AUDIENCE_SCENARIOS.length}`;
    $("audience-scenario-text").textContent = scenario.text;
    hide($("audience-feedback"));
    hide($("audience-next"));
    document.querySelectorAll(".btn--vote").forEach((b) => {
      b.classList.remove("selected");
      b.disabled = false;
    });
    audienceVoted = false;
  }

  function initAudience() {
    document.querySelectorAll(".btn--vote").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (audienceVoted) return;
        audienceVoted = true;
        document.querySelectorAll(".btn--vote").forEach((b) => {
          b.disabled = true;
          if (b === btn) b.classList.add("selected");
        });

        const scenario = AUDIENCE_SCENARIOS[audienceIndex];
        const meta = CLASSIFICATION_META[scenario.classification];
        const feedback = $("audience-feedback");
        feedback.innerHTML = "";

        const classificationEl = document.createElement("div");
        classificationEl.className = "audience-feedback__classification callout " + meta.className;
        classificationEl.textContent = "Clasificación recomendada: " + meta.label;
        feedback.appendChild(classificationEl);

        const explanationEl = document.createElement("p");
        explanationEl.textContent = scenario.explanation;
        feedback.appendChild(explanationEl);

        show(feedback);

        if (audienceIndex < AUDIENCE_SCENARIOS.length - 1) {
          show($("audience-next"));
        }
      });
    });

    $("audience-next").addEventListener("click", () => {
      audienceIndex = Math.min(audienceIndex + 1, AUDIENCE_SCENARIOS.length - 1);
      renderAudienceScenario();
    });

    $("audience-reset").addEventListener("click", () => {
      audienceIndex = 0;
      renderAudienceScenario();
    });

    renderAudienceScenario();
  }

  // -------------------------------------------------------------------
  // Modo presentación y reinicio global
  // -------------------------------------------------------------------

  function initPresentationMode() {
    const btn = $("presentation-toggle");
    btn.addEventListener("click", () => {
      const active = document.body.classList.toggle("presentation-mode");
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function initGlobalReset() {
    $("global-reset").addEventListener("click", () => {
      window.location.reload();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    loadCase();
    initScenario1();
    initScenario2();
    initScenario3();
    initAudience();
    initPresentationMode();
    initGlobalReset();
  });
})();
