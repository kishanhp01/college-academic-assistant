let studyPlan = [];


// =================================
// GENERATE STUDY PLAN
// =================================

function generatePlan() {

    const subject =
        document.getElementById("subject").value.trim();

    const topic =
        document.getElementById("topic").value.trim();

    const examDate =
        document.getElementById("examDate").value;

    const difficulty =
        document.getElementById("difficulty").value;

    const duration =
        document.getElementById("duration").value;


    // Check input

    if (
        subject === "" ||
        topic === "" ||
        examDate === "" ||
        duration === ""
    ) {

        alert("Please fill all the fields.");

        return;
    }


    // Create task

    const task = {

        id: Date.now(),

        subject: subject,

        topic: topic,

        examDate: examDate,

        difficulty: difficulty,

        duration: duration,

        completed: false

    };


    // Add task

    studyPlan.push(task);


    // Show task

    displayPlan();


    // Clear form

    document.getElementById("subject").value = "";

    document.getElementById("topic").value = "";

    document.getElementById("examDate").value = "";

    document.getElementById("duration").value = "";

}



// =================================
// DISPLAY STUDY PLAN
// =================================

function displayPlan() {

    const container =
        document.getElementById("studyPlan");


    // Clear old display

    container.innerHTML = "";


    // Display each task

    studyPlan.forEach(function(task) {

        const taskDiv =
            document.createElement("div");


        taskDiv.className = "plan-task";


        taskDiv.innerHTML = `

            <h3>
                ${task.subject}
            </h3>

            <p>
                <strong>Topic:</strong>
                ${task.topic}
            </p>

            <p>
                <strong>Exam Date:</strong>
                ${task.examDate}
            </p>

            <p>
                <strong>Difficulty:</strong>
                ${task.difficulty}
            </p>

            <p>
                <strong>Duration:</strong>
                ${task.duration} hour(s)
            </p>

            <p>
                <strong>Status:</strong>
                ${task.completed ? "Completed" : "Pending"}
            </p>

            <button
                onclick="completeTask(${task.id})">

                Complete

            </button>

            <button
                onclick="deleteTask(${task.id})">

                Delete

            </button>

        `;


        container.appendChild(taskDiv);

    });


    updateProgress();

}



// =================================
// COMPLETE TASK
// =================================

function completeTask(id) {

    studyPlan.forEach(function(task) {

        if (task.id === id) {

            task.completed = true;

        }

    });


    displayPlan();

}



// =================================
// DELETE TASK
// =================================

function deleteTask(id) {

    studyPlan =
        studyPlan.filter(function(task) {

            return task.id !== id;

        });


    displayPlan();

}



// =================================
// UPDATE PROGRESS
// =================================

function updateProgress() {

    const total =
        studyPlan.length;


    const completed =
        studyPlan.filter(function(task) {

            return task.completed;

        }).length;


    let percentage = 0;


    if (total > 0) {

        percentage =
            Math.round(
                (completed / total) * 100
            );

    }


    const progress =
        document.getElementById("plannerProgress");


    const progressText =
        document.getElementById("progressText");


    progress.style.width =
        percentage + "%";


    progressText.textContent =
        percentage + "% Completed";

}