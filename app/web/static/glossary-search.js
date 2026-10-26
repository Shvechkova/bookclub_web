/* Поиск по словарю клуба — в браузере: у статической выгрузки нет сервера.
   Текст для поиска сервер уже положил в карточки (`data-search`, `data-names`)
   нормализованным; здесь те же правила применяются к запросу: строчные буквы,
   «ё» как «е», всё, что не буква и не цифра, — пробел (см. app/web/search.py).
   Текст данных в разметку не вставляется: подсветка собирается из текстовых
   узлов и элементов <mark>. */
(function () {
  "use strict";

  var form = document.querySelector(".glossary-search");
  if (!form) return;
  var field = form.querySelector("input[type=search]");
  var found = form.querySelector(".glossary-found");
  var nothing = form.querySelector(".glossary-nothing");
  var list = document.querySelector(".glossary-list");
  var sections = Array.prototype.slice.call(list.querySelectorAll("section.letter"));
  var letterLinks = Array.prototype.slice.call(document.querySelectorAll(".letters a"));
  var NOT_A_WORD = /[^\p{L}\p{N}]/u;

  function fold(ch) {
    var lower = ch.toLowerCase();
    if (lower.length !== 1) lower = ch;
    if (lower === "ё") return "е";
    return NOT_A_WORD.test(lower) ? " " : lower;
  }

  // Посимвольно, без схлопывания пробелов: позиции совпадают с исходным
  // текстом, и по ним можно подсвечивать.
  function foldChars(text) {
    var out = "";
    for (var i = 0; i < text.length; i++) out += fold(text.charAt(i));
    return out;
  }

  function normalize(text) {
    return foldChars(text).replace(/ +/g, " ").trim();
  }

  // Исходный порядок и исходный текст — чтобы вернуть всё, как было.
  var entries = [];
  sections.forEach(function (section, sectionIndex) {
    section.dataset.order = sectionIndex;
    Array.prototype.forEach.call(section.querySelectorAll("article.entry"), function (article, index) {
      var marked = Array.prototype.slice.call(article.querySelectorAll(".entry-name, .entry-aliases"));
      entries.push({
        article: article,
        section: section,
        order: index,
        text: article.dataset.search || "",
        names: (article.dataset.names || "").split("|"),
        marked: marked.map(function (node) { return { node: node, text: node.textContent }; })
      });
    });
  });

  // 0 — название или синоним начинается с запроса, 1 — все слова в названии
  // или синониме, 2 — остальное; -1 — не найдено.
  function rank(entry, query, words) {
    for (var i = 0; i < words.length; i++) {
      if (entry.text.indexOf(words[i]) === -1) return -1;
    }
    var best = 2;
    entry.names.forEach(function (name) {
      if (name.indexOf(query) === 0) best = 0;
      else if (best > 1 && words.every(function (word) { return name.indexOf(word) !== -1; })) best = 1;
    });
    return best;
  }

  function highlight(item, words) {
    var node = item.node;
    var text = item.text;
    while (node.firstChild) node.removeChild(node.firstChild);
    if (!words.length) {
      node.textContent = text;
      return;
    }
    var folded = foldChars(text);
    var marks = new Array(text.length);
    words.forEach(function (word) {
      var at = folded.indexOf(word);
      while (at !== -1) {
        for (var i = at; i < at + word.length; i++) marks[i] = true;
        at = folded.indexOf(word, at + word.length);
      }
    });
    var start = 0;
    while (start < text.length) {
      var end = start;
      while (end < text.length && !!marks[end] === !!marks[start]) end++;
      var piece = document.createTextNode(text.slice(start, end));
      if (marks[start]) {
        var mark = document.createElement("mark");
        mark.appendChild(piece);
        node.appendChild(mark);
      } else {
        node.appendChild(piece);
      }
      start = end;
    }
  }

  function byOrder(a, b) { return a.order - b.order; }

  function apply(raw) {
    var query = normalize(raw);
    var words = query ? query.split(" ") : [];
    var total = 0;
    // Одна буква среди других слов («brooks's» → «brooks s») подсветила бы
    // половину текста: подсвечиваются только слова от двух букв.
    var shown = words.length > 1 ? words.filter(function (word) { return word.length > 1; }) : words;
    var groups = sections.map(function (section) {
      return { section: section, order: Number(section.dataset.order), best: 3, items: [] };
    });

    entries.forEach(function (entry) {
      var score = words.length ? rank(entry, query, words) : 0;
      entry.score = score;
      entry.article.hidden = score === -1;
      entry.marked.forEach(function (item) { highlight(item, score === -1 ? [] : shown); });
      if (score === -1) return;
      total++;
      var group = groups[Number(entry.section.dataset.order)];
      group.items.push(entry);
      if (score < group.best) group.best = score;
    });

    groups.forEach(function (group) {
      group.items.sort(function (a, b) { return a.score - b.score || a.order - b.order; });
      group.items.forEach(function (entry) { group.section.appendChild(entry.article); });
      group.section.hidden = group.items.length === 0;
      letterLinks[group.order].hidden = group.items.length === 0;
    });
    groups
      .slice()
      .sort(function (a, b) { return a.best - b.best || byOrder(a, b); })
      .forEach(function (group) { list.appendChild(group.section); });

    found.textContent = words.length ? "Найдено: " + total : "";
    nothing.hidden = !(words.length && total === 0);
    remember(raw.trim() ? raw : "");
  }

  function remember(raw) {
    var params = new URLSearchParams(location.search);
    if (raw) params.set("q", raw);
    else params.delete("q");
    var search = params.toString();
    var next = location.pathname + (search ? "?" + search : "") + location.hash;
    if (next !== location.pathname + location.search + location.hash) {
      history.replaceState(history.state, "", next);
    }
  }

  var timer = null;
  function schedule() {
    clearTimeout(timer);
    timer = setTimeout(function () { apply(field.value); }, 100);
  }

  function clear() {
    clearTimeout(timer);
    field.value = "";
    apply("");
  }

  field.addEventListener("input", schedule);
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    clearTimeout(timer);
    apply(field.value);
  });
  field.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      event.preventDefault();
      clear();
    }
  });

  function typingElsewhere(target) {
    if (!target || !target.tagName) return false;
    var tag = target.tagName.toLowerCase();
    return tag === "input" || tag === "textarea" || tag === "select" || target.isContentEditable;
  }

  document.addEventListener("keydown", function (event) {
    if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey) return;
    if (typingElsewhere(event.target)) return;
    event.preventDefault();
    field.focus();
    field.select();
  });

  // Якорь внутри словаря: понятие, на которое ведёт ссылка, может быть скрыто
  // запросом. Запрос сбрасывается до перехода, и браузер прокручивает к
  // видимому понятию.
  document.addEventListener("click", function (event) {
    var link = event.target.closest ? event.target.closest("a[href^='#']") : null;
    if (link && field.value) clear();
  });

  function revealHash() {
    var id = decodeURIComponent(location.hash.slice(1));
    var target = id && document.getElementById(id);
    if (!target || !list.contains(target) || !target.closest("[hidden]")) return;
    clear();
    target.scrollIntoView();
  }
  window.addEventListener("hashchange", revealHash);

  // Открытие страницы: якорь сильнее запроса — по ссылке пришли к понятию.
  var initial = new URLSearchParams(location.search).get("q") || "";
  var hashId = location.hash ? decodeURIComponent(location.hash.slice(1)) : "";
  if (hashId && document.getElementById(hashId) && list.contains(document.getElementById(hashId))) {
    remember("");
  } else if (initial) {
    field.value = initial;
    apply(initial);
  }
})();
