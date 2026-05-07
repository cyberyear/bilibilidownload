const state = {
  selectedVideo: null,
  pollingTimer: null,
  currentQuery: "",
  currentPage: 1,
  hasMore: false,
  currentOrder: "totalrank",
};

const queryInput = document.getElementById("query");
const orderSelect = document.getElementById("search-order");
const outputDirInput = document.getElementById("output-dir");
const selectDirBtn = document.getElementById("select-dir-btn");
const fileNameInput = document.getElementById("file-name");
const browserSelect = document.getElementById("cookies-browser");
const searchStatus = document.getElementById("search-status");
const resultsContainer = document.getElementById("results");
const jobsContainer = document.getElementById("jobs");
const paginationContainer = document.getElementById("pagination");
const prevPageBtn = document.getElementById("prev-page");
const nextPageBtn = document.getElementById("next-page");
const pageInfo = document.getElementById("page-info");
const resultTemplate = document.getElementById("result-template");
const jobTemplate = document.getElementById("job-template");

// 文件夹选择功能
selectDirBtn.addEventListener("click", async () => {
  try {
    // 使用 File System Access API（现代浏览器支持）
    if ("showDirectoryPicker" in window) {
      const dirHandle = await window.showDirectoryPicker({
        mode: "readwrite",
        startIn: "downloads",
      });
      // 获取完整路径
      const path = await getDirectoryPath(dirHandle);
      outputDirInput.value = path;
    } else {
      // 回退方案：使用 input[type=file] webkitdirectory
      const input = document.createElement("input");
      input.type = "file";
      input.webkitdirectory = true;
      input.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
          const file = e.target.files[0];
          // 提取文件夹路径（去掉文件名）
          const filePath = file.webkitRelativePath;
          const dirPath = filePath.substring(0, filePath.lastIndexOf("/"));
          outputDirInput.value = dirPath;
        }
      });
      input.click();
    }
  } catch (err) {
    if (err.name !== "AbortError") {
      console.error("选择文件夹失败:", err);
      alert("选择文件夹失败，请手动输入路径");
    }
  }
});

// 获取文件夹完整路径
async function getDirectoryPath(dirHandle) {
  // 尝试获取真实路径
  try {
    const path = await dirHandle.resolve();
    // 如果能获取到路径，返回
    if (path && path.length > 0) {
      return path.join("/");
    }
  } catch (e) {
    // 忽略错误
  }

  // 回退方案：使用文件夹名称
  return dirHandle.name;
}

document.getElementById("search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (query.length < 1) {
    searchStatus.textContent = "请输入搜索关键词。";
    return;
  }

  state.currentQuery = query;
  state.currentPage = 1;
  state.currentOrder = orderSelect.value;
  await doSearch();
});

// 排序方式变化时重新搜索
orderSelect.addEventListener("change", async () => {
  if (state.currentQuery) {
    state.currentPage = 1;
    state.currentOrder = orderSelect.value;
    await doSearch();
  }
});

prevPageBtn.addEventListener("click", async () => {
  if (state.currentPage > 1) {
    state.currentPage--;
    await doSearch();
  }
});

nextPageBtn.addEventListener("click", async () => {
  if (state.hasMore) {
    state.currentPage++;
    await doSearch();
  }
});

async function doSearch() {
  searchStatus.textContent = "正在搜索...";
  searchStatus.style.color = "#666";
  resultsContainer.innerHTML = "";
  paginationContainer.style.display = "none";

  try {
    const response = await fetch(
      `/api/search?q=${encodeURIComponent(state.currentQuery)}&page=${state.currentPage}&order=${state.currentOrder}`
    );
    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "搜索失败");
    }
    const data = await response.json();
    renderResults(data.results);
    searchStatus.style.color = "#333";

    if (data.results.length === 0) {
      searchStatus.textContent = "没有找到结果，请尝试其他关键词";
    } else if (data.has_more) {
      searchStatus.textContent = `当前第 ${data.page} 页，可继续翻页查看更多`;
    } else {
      searchStatus.textContent = `当前第 ${data.page} 页，已显示全部结果`;
    }

    // 更新翻页控件
    state.hasMore = data.has_more;
    updatePagination(data.page, data.total);

  } catch (error) {
    searchStatus.style.color = "#e74c3c";
    searchStatus.textContent = `搜索失败: ${error.message}`;
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
}

function updatePagination(page, total) {
  if (total > 0) {
    paginationContainer.style.display = "flex";
    prevPageBtn.disabled = page <= 1;
    nextPageBtn.disabled = !state.hasMore;
    pageInfo.textContent = `第 ${page} 页`;
  } else {
    paginationContainer.style.display = "none";
  }
}

function renderResults(items) {
  resultsContainer.innerHTML = "";
  if (!items.length) {
    return;
  }

  for (const item of items) {
    const node = resultTemplate.content.firstElementChild.cloneNode(true);
    const titleLink = node.querySelector(".title-link");
    titleLink.textContent = item.title;
    titleLink.href = item.url;
    node.querySelector(".author").textContent = `UP 主: ${item.author || "未知"} | BV: ${item.bvid}`;
    node.querySelector(".description").textContent = item.description || "没有简介";
    node.querySelector(".duration").textContent = `时长: ${item.duration || "未知"}`;
    node.querySelector(".btn-video").addEventListener("click", () => startDownload(item, false));
    node.querySelector(".btn-audio").addEventListener("click", () => startDownload(item, true));
    resultsContainer.appendChild(node);
  }
}

async function startDownload(item, audioOnly) {
  console.log("startDownload called, audioOnly:", audioOnly, "item:", item.title);

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
    audio_only: audioOnly,
  };

  console.log("Sending payload:", payload);

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
    console.log("Job created:", job);
    await refreshJobs();
    beginPolling();
    const formatText = audioOnly ? "音频" : "视频";
    searchStatus.textContent = `已创建${formatText}下载任务: ${job.title}`;
  } catch (error) {
    console.error("Download error:", error);
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

    // 更新进度条
    const progressBarFill = node.querySelector(".progress-bar-fill");
    const progressText = node.querySelector(".progress-text");
    progressBarFill.style.width = `${job.percent}%`;
    progressText.textContent = `${job.percent.toFixed(1)}%`;

    // 设置状态属性，用于 CSS 样式
    node.setAttribute("data-status", job.status);

    node.querySelector(".progress").textContent = job.progress;
    node.querySelector(".file").textContent = job.downloaded_path
      ? `文件: ${job.downloaded_path}`
      : `目录: ${job.output_dir}`;
    node.querySelector(".error").textContent = job.error || "";

    // 删除按钮事件
    const deleteBtn = node.querySelector(".btn-delete");
    deleteBtn.addEventListener("click", async () => {
      if (confirm("确定要删除这条下载记录吗？")) {
        await deleteJob(job.id);
      }
    });

    jobsContainer.appendChild(node);
  }
}

async function deleteJob(jobId) {
  try {
    const response = await fetch(`/api/jobs/${jobId}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error("删除失败");
    }
    await refreshJobs();
  } catch (error) {
    alert("删除任务失败: " + error.message);
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
