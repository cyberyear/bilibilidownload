const state = {
  selectedVideo: null,
  pollingTimer: null,
};

const queryInput = document.getElementById("query");
const outputDirInput = document.getElementById("output-dir");
const fileNameInput = document.getElementById("file-name");
const browserSelect = document.getElementById("cookies-browser");
const searchStatus = document.getElementById("search-status");
const resultsContainer = document.getElementById("results");
const jobsContainer = document.getElementById("jobs");
const resultTemplate = document.getElementById("result-template");
const jobTemplate = document.getElementById("job-template");

document.getElementById("search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (query.length < 2) {
    searchStatus.textContent = "请输入至少 2 个字符。";
    return;
  }

  searchStatus.textContent = "正在搜索...";
  searchStatus.style.color = "#666";
  resultsContainer.innerHTML = "";

  try {
    const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "搜索失败");
    }
    const items = await response.json();
    renderResults(items);
    searchStatus.style.color = "#333";
    if (items.length === 0) {
      searchStatus.textContent = "没有找到结果，请尝试其他关键词";
    } else {
      searchStatus.textContent = `找到 ${items.length} 条结果`;
    }
  } catch (error) {
    searchStatus.style.color = "#e74c3c";
    searchStatus.textContent = `搜索失败: ${error.message}`;
    // 显示重试提示
    if (error.message.includes("风控") || error.message.includes("频繁") || error.message.includes("超时")) {
      resultsContainer.innerHTML = `
        <div style="text-align: center; padding: 20px; color: #666;">
          <p>💡 建议：</p>
          <p>1. 等待几秒后重试</p>
          <p>2. 更换搜索关键词</p>
          <p>3. 检查网络连接</p>
        </div>
      `;
    }
  }
});

function renderResults(items) {
  resultsContainer.innerHTML = "";
  if (!items.length) {
    return;
  }

  for (const item of items) {
    const node = resultTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector("h3").textContent = item.title;
    node.querySelector(".author").textContent = `UP 主: ${item.author || "未知"} | BV: ${item.bvid}`;
    node.querySelector(".description").textContent = item.description || "没有简介";
    node.querySelector(".duration").textContent = `时长: ${item.duration || "未知"}`;
    node.querySelector("button").addEventListener("click", () => startDownload(item));
    resultsContainer.appendChild(node);
  }
}

async function startDownload(item) {
  const outputDir = outputDirInput.value.trim();
  if (!outputDir) {
    alert("请先填写保存目录。");
    return;
  }

  const payload = {
    url: item.url,
    title: item.title,
    output_dir: outputDir,
    file_name: fileNameInput.value.trim() || null,
    cookies_browser: browserSelect.value === "none" ? null : browserSelect.value,
  };

  try {
    const response = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || "创建下载任务失败");
    }
    const job = await response.json();
    await refreshJobs();
    beginPolling();
    searchStatus.textContent = `已创建下载任务: ${job.title}`;
  } catch (error) {
    alert(error.message);
  }
}

async function refreshJobs() {
  const response = await fetch("/api/jobs");
  const jobs = await response.json();
  renderJobs(jobs);
}

function renderJobs(jobs) {
  jobsContainer.innerHTML = "";
  if (!jobs.length) {
    jobsContainer.classList.add("empty");
    jobsContainer.textContent = "还没有下载任务";
    return;
  }

  jobsContainer.classList.remove("empty");
  for (const job of jobs) {
    const node = jobTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector("h3").textContent = job.title;
    node.querySelector(".badge").textContent = job.status;
    node.querySelector(".progress").textContent = `${job.progress} (${job.percent.toFixed(1)}%)`;
    node.querySelector(".file").textContent = job.downloaded_path
      ? `文件: ${job.downloaded_path}`
      : `目录: ${job.output_dir}`;
    node.querySelector(".error").textContent = job.error || "";
    jobsContainer.appendChild(node);
  }
}

function beginPolling() {
  if (state.pollingTimer) {
    return;
  }

  state.pollingTimer = window.setInterval(async () => {
    await refreshJobs();
    const cards = [...jobsContainer.querySelectorAll(".badge")].map((node) => node.textContent);
    const active = cards.some((status) => ["queued", "starting", "downloading", "processing"].includes(status));
    if (!active) {
      window.clearInterval(state.pollingTimer);
      state.pollingTimer = null;
    }
  }, 1500);
}

refreshJobs();
