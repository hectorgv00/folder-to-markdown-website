// filepath: /c:/Proyectos/Proyectos_propios/folder-to-markdown-website/scripts/script.js
let droppedFile = null;

document.addEventListener("DOMContentLoaded", () => {
  const dropaera = document.getElementById("droparea");
  let dragCounter = 0;

  setDragOver(dropaera, dragCounter);
  setDrop(dropaera, dragCounter);
  setDragLeave(dropaera, dragCounter);
});

const getInput = (file) => {
  const name = file.name;
  const extension = name.split(".").pop();

  if (extension !== "zip") {
    alert("The file must be a zip file");
    return;
  }

  setFilename(name);
  changeIcon();

  droppedFile = file;
  allowConvert();
};

const setFilename = (name) => {
  const filename = document.getElementById("filename");
  filename.innerHTML = name;
};

const changeIcon = () => {
  const icon = document.getElementById("icon");
  icon.src = "assets/images/yes.svg";
};

const setDragOver = (dropaera, dragCounter) => {
  document.body.addEventListener("dragover", (event) => {
    event.preventDefault();
    dragCounter++;

    dropaera.style.display = "flex";

    console.log(event);
  });
};

const setDrop = (dropaera, dragCounter) => {
  document.addEventListener("drop", (event) => {
    event.preventDefault();

    const file = event.dataTransfer.files[0];
    getInput(file);
    dropaera.style.display = "none";
    dragCounter = 0;
  });
};

const setDragLeave = (dropaera, dragCounter) => {
  document.body.addEventListener("dragleave", (event) => {
    event.preventDefault();
    dragCounter--;
    if (dragCounter === 0) {
      dropaera.style.display = "none";
    }
    if (
      event.screenX === 0 &&
      event.screenY === 0 &&
      event.clientX === 0 &&
      event.clientY === 0
    ) {
      dropaera.style.display = "none";
      dragCounter = 0;
    }
    console.log(event);
  });
};

const allowConvert = () => {
  const convertButton = document.querySelector("button");
  convertButton.classList.remove("disabled");
};

const sendDataToPython = (event) => {
  event.preventDefault();
  console.log(event);
  renderFile(droppedFile);
};

// filepath: /c:/Proyectos/Proyectos_propios/folder-to-markdown-website/scripts/script.js
const renderFile = (file) => {
  const reader = new FileReader();
  reader.readAsDataURL(file);
  reader.onload = () => {
    console.log(reader.result);
    const base64 = reader.result;
    sendBase64(base64);
    console.log(base64);
  };

  reader.onerror = (error) => {
    console.log(error);
  };
};

const sendBase64 = async (base64) => {
  try {
    const response = await fetch(
      "https://zip-to-markdown-api.hectorgv00.online/convert",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ base64 }),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = url;
    a.download = "output.md";
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error("Error:", error);
  }
};
