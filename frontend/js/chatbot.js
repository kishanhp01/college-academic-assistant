function sendMessage() {

    const input =
        document.getElementById("message");

    const chatBox =
        document.getElementById("chatBox");

    const message =
        input.value.trim();


    if (message === "") {
        return;
    }


    const studentMessage =
        document.createElement("div");

    studentMessage.className =
        "student-message";

    studentMessage.textContent =
        message;


    chatBox.appendChild(studentMessage);


    input.value = "";


    // Temporary response
    const aiMessage =
        document.createElement("div");

    aiMessage.className =
        "ai-message";

    aiMessage.textContent =
        "This is a temporary AI response. The actual AI/RAG system will be connected later.";


    chatBox.appendChild(aiMessage);


    chatBox.scrollTop =
        chatBox.scrollHeight;
}