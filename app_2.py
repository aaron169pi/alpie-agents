import streamlit as st
import httpx
import json
import re
from dotenv import load_dotenv
import os
load_dotenv()

API_KEY = os.getenv("PI_API_KEY")
API_URL = os.getenv("PI_MODEL_ENDPOINT")
MODEL = "alpie-32b"


st.set_page_config(page_title="Study AI", page_icon="🎓", layout="wide")


st.sidebar.title("⚙️ Study Mode")

mode = st.sidebar.radio(
    "Choose Mode",
    ["Learning", "Flashcards", "Quiz"]
)
with st.spinner(f"Analyzing the quuery"):
    pass

if mode == "Quiz":
    num_questions = st.sidebar.slider("Number of Questions", 1, 20, 5)
else:
    num_questions = None

st.sidebar.markdown("---")
st.sidebar.caption("Your AI Study Companion 📚")

# ------------------- MAIN TITLE -------------------
st.title("🎓 AI Study Assistant")

# Create Session Memory
if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_flashcard" not in st.session_state:
    st.session_state.current_flashcard = 0

if "flashcard_data" not in st.session_state:
    st.session_state.flashcard_data = []

if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = []

if "last_learning_response" not in st.session_state:
    st.session_state.last_learning_response = None





def get_system_prompt(mode_type):
    """Returns detailed system prompts for each mode"""
    
    prompts = {
        "Learning": """You are an expert educator with a gift for making complex topics accessible and engaging. Your teaching style is:

1. **Clear Structure**: Start with a simple definition, then build complexity gradually
2. **Real-World Examples**: Always provide 2-3 concrete, relatable examples
3. **Analogies**: Use metaphors to explain abstract concepts
4. **Key Takeaways**: End with 3-5 bullet points summarizing the core concepts
5. **Engagement**: Ask thought-provoking questions to encourage deeper thinking

Format your response with:
- An engaging introduction
- Main explanation broken into digestible sections
- Practical examples with context
- A summary of key points
- Optional: Suggestions for further exploration

Keep language clear, avoid jargon unless necessary (and explain it when used), and maintain an encouraging, conversational tone.""",

        "Flashcards": """You are a flashcard generator that creates effective study materials. Generate EXACTLY 5 flashcards in the following JSON format:

[
  {
    "question": "Clear, specific question on the front",
    "answer": "Concise, informative answer on the back",
     "front_color": ["", ""],
    "back_color": ["", ""]
  }
]

Rules for flashcard creation:
- For `front_color` and `back_color`, provide an array of two complementary hex color codes to create a linear gradient.Each time it should be different from previous flashcards.
- Flashcards has text in white color so choose colors accordingly so that text is clearly visible.
- Questions should test understanding, not just recall
- Keep questions focused on ONE concept each
- Answers should be 2-4 sentences maximum
- Use active recall principles
- Progress from basic to more advanced concepts
- Avoid yes/no questions
- Choose a different, visually appealing color palette

Return ONLY the JSON array, no additional text or markdown formatting.""",

        "Quiz": """You are a quiz generator. Generate quiz questions in the following JSON format:

[
  {
    "question": "Question text here",
    "options": ["Option A text", "Option B text", "Option C text", "Option D text"],
    "correct_index": 0,
    "explanation": "Detailed explanation of why this answer is correct"
  }
]

Rules:
- Create engaging, clear questions
- Provide exactly 4 options per question
- correct_index is 0-based (0 for first option, 1 for second, etc.)
- Make wrong options plausible but clearly incorrect
- Provide detailed explanations (2-3 sentences)
- Test understanding, not just memorization

Return ONLY the JSON array, no additional text or markdown formatting."""
    }
    
    return prompts.get(mode_type, "")


def format_message(mode_type, user_text, num_questions_local=None, context=None):
    """Creates structured prompts based on study mode"""
    
    system_prompt = get_system_prompt(mode_type)
    
    if mode_type == "Learning":
        return f"""{system_prompt}

Topic to explain: {user_text}

Please provide a comprehensive yet accessible explanation of this topic."""
    if context:
        source_text = f"based on the following text:\n\n---\n{context}\n---"
    else:
        source_text = f"on the topic: {user_text}"
    if mode_type == "Flashcards":
        return f"""{system_prompt}

Topic: {user_text}

Generate 5 flashcards {source_text}"""

    elif mode_type == "Quiz":
        questions_to_gen = num_questions_local if num_questions_local is not None else 5
        return f"""{system_prompt}

Please generate {questions_to_gen} multiple-choice questions {source_text} ,  multiple-choice questions {source_text}. Ensure the position of the correct answer (correct_index) is varied and randomized across the questions."""


# ------------------- STREAM FUNCTION -------------------

def stream_llm(message):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
    }

    payload = {
        "model": MODEL,
        "stream": True,
        "messages": [{"role": "user", "content": message}],
        "max_tokens": 16000
    }

    with httpx.Client(timeout=None) as client:
        with client.stream("POST", API_URL, headers=headers, json=payload) as response:
            for line in response.iter_lines():
                if not line:
                    continue
                if line == "data: [DONE]":
                    return
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        yield data["choices"][0]["delta"].get("content", "")
                    except:
                        continue


# ------------------- FLASHCARD HTML GENERATOR -------------------

def generate_flashcard_html(flashcards):
    """Generates interactive HTML/CSS flashcards with flip animation"""
    
    html = """
    <style>
        .flashcard-container {
            perspective: 1000px;
            margin: 20px auto;
            max-width: 600px;
            min-height: 450px;
        }

        .flashcard {
            position: relative;
            width: 100%;
            height: 300px;
            transition: transform 0.6s;
            transform-style: preserve-3d;
            cursor: pointer;
            border-radius: 15px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            margin-bottom: 60px;
        }
        
        .flashcard.flipped {
            transform: rotateY(180deg);
        }
        
        .flashcard-face {
            position: absolute;
            width: 100%;
            height: 100%;
            backface-visibility: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 30px;
            border-radius: 15px;
            font-size: 1.2em;
            text-align: center;
            box-sizing: border-box;
            overflow: auto;
        }
                
        .flashcard-front {
            color: white;
        }
        
        .flashcard-back {
            color: white;
            transform: rotateY(180deg);
        }
        
        .nav-buttons {
            display: flex;
            justify-content: space-between;
            margin-top: 15px;
            gap: 10px;
            position: relative;
            z-index: 10;
        }
        
        .nav-btn {
            padding: 10px 20px;
            font-size: 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            color: white;
            transition: background 0.3s, filter 0.3s;
        }
        
        .nav-btn:hover {
            filter: brightness(110%);
        }
        
        .nav-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            filter: none;
        }
        
        .card-counter {
            text-align: center;
            margin: 15px 0;
            font-size: 1.1em;
            color: #667eea;
            font-weight: bold;
        }
        
        .hint {
            text-align: center;
            color: #666;
            font-style: italic;
            margin-top: 10px;
        }
    </style>
    
    <div class="flashcard-container">
        <div class="card-counter" id="cardCounter"></div>
        
        <div class="flashcard" id="flashcard" onclick="flipCard()">
            <div class="flashcard-face flashcard-front">
                <div id="questionText"></div>
            </div>
            <div class="flashcard-face flashcard-back">
                <div id="answerText"></div>
            </div>
        </div>
        
        <div class="hint">Click card to flip</div>
        
        <div class="nav-buttons">
            <button class="nav-btn" id="prevBtn" onclick="previousCard()" disabled>← Previous</button>
            <button class="nav-btn" id="nextBtn" onclick="nextCard()">Next →</button>
        </div>
    </div>
    
    <script>
        const flashcards = """ + json.dumps(flashcards) + """;
        let currentCard = 0;
        let isFlipped = false;

        const card = document.getElementById('flashcard');
        const frontFace = card.querySelector('.flashcard-front');
        const backFace = card.querySelector('.flashcard-back');
        const questionText = document.getElementById('questionText');
        const answerText = document.getElementById('answerText');
        const counter = document.getElementById('cardCounter');
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        
        function flipCard() {
            card.classList.toggle('flipped');
            isFlipped = !isFlipped;
        }
        
        function updateCard() {
            const currentFlashcardData = flashcards[currentCard];
            
            if (isFlipped) {
                card.classList.remove('flipped');
                isFlipped = false;
            }
            
            questionText.textContent = currentFlashcardData.question;
            answerText.textContent = currentFlashcardData.answer;
            counter.textContent = `Card ${currentCard + 1} of ${flashcards.length}`;
            
            const frontColor = currentFlashcardData.front_color;
            const backColor = currentFlashcardData.back_color;
            
            frontFace.style.background = `linear-gradient(135deg, ${frontColor[0]} 0%, ${frontColor[1]} 100%)`;
            backFace.style.background = `linear-gradient(135deg, ${backColor[0]} 0%, ${backColor[1]} 100%)`;
            
            prevBtn.style.background = frontColor[0];
            nextBtn.style.background = frontColor[0];
            
            prevBtn.disabled = currentCard === 0;
            nextBtn.disabled = currentCard === flashcards.length - 1;
        }
        
        function nextCard() {
            if (currentCard < flashcards.length - 1) {
                currentCard++;
                updateCard();
            }
        }
        
        function previousCard() {
            if (currentCard > 0) {
                currentCard--;
                updateCard();
            }
        }
        
        updateCard();
        
        document.addEventListener('keydown', function(event) {
            if (event.key === 'ArrowRight') nextCard();
            if (event.key === 'ArrowLeft') previousCard();
            if (event.key === ' ') flipCard();
        });
    </script>
    """
    
    return html


# ------------------- QUIZ HTML GENERATOR -------------------

def generate_quiz_html(quiz_questions):
    """Generates interactive quiz interface matching the screenshot design"""
    
    html = """
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        .quiz-container {
            max-width: 800px;
            margin: 20px auto 50px auto;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0d1117;
            border-radius: 12px;
            padding: 30px;
            color: white;
        }
        
        .quiz-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #30363d;
        }
        
        .question-counter {
            font-size: 18px;
            color: #8b949e;
        }
        
        .question-text {
            font-size: 22px;
            font-weight: 600;
            margin-bottom: 30px;
            line-height: 1.5;
            color: #ffffff;
        }
        
        .options-container {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-bottom: 30px;
        }
        
        .option {
            background: #161b22;
            border: 2px solid #30363d;
            border-radius: 8px;
            padding: 16px 20px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 16px;
        }
        
        .option:hover:not(.selected):not(.disabled) {
            border-color: #58a6ff;
            background: #1c2128;
        }
        
        .option.selected {
            background: #1c2128;
            border-color: #58a6ff;
        }
        
        .option.correct {
            background: #0d4421;
            border-color: #2ea043;
            color: #2ea043;
        }
        
        .option.wrong {
            background: #4c1f1f;
            border-color: #f85149;
            color: #f85149;
        }
        
        .option.disabled {
            cursor: not-allowed;
            opacity: 0.7;
        }
        
        .option-label {
            font-weight: 600;
            min-width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
            background: #30363d;
            font-size: 14px;
        }
        
        .option.correct .option-label {
            background: #2ea043;
            color: white;
        }
        
        .option.wrong .option-label {
            background: #f85149;
            color: white;
        }
        
        .option-icon {
            margin-left: auto;
            font-size: 20px;
        }
        
        .explanation-box {
            background: #1c2128;
            border-left: 4px solid #2ea043;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 20px;
            display: none;
        }
        
        .explanation-box.show {
            display: block;
        }
        
        .explanation-title {
            font-weight: 600;
            margin-bottom: 10px;
            color: #2ea043;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .correct-option-label {
            background: #2ea043;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 14px;
        }
        
        .explanation-text {
            color: #c9d1d9;
            line-height: 1.6;
        }
        
        .nav-buttons {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            margin-top: 20px;
        }
        
        .quiz-btn {
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            flex: 1;
        }
        
        .btn-explain {
            background: #238636;
            color: white;
            display: none;
        }
        
        .btn-explain.show {
            display: block;
        }
        
        .btn-explain:hover {
            background: #2ea043;
        }
        
        .btn-previous {
            background: #30363d;
            color: white;
        }
        
        .btn-previous:hover:not(:disabled) {
            background: #484f58;
        }
        
        .btn-next {
            background: #58a6ff;
            color: white;
        }
        
        .btn-next:hover:not(:disabled) {
            background: #79c0ff;
        }
        
        .quiz-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .quiz-btn.hidden {
            display: none;
        }

        .results-container {
            display: none; /* Hidden by default */
            text-align: center;
            padding: 40px 20px;
        }

        .results-header {
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 40px;
            color: #e6edf3;
        }

        .stats-container {
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
        }

        .stat-box {
            background: #161b22;
            border-radius: 8px;
            padding: 20px;
            min-width: 180px;
            text-align: left;
            flex: 1;
        }

        .stat-box .label {
            font-size: 16px;
            color: #8b949e;
            margin-bottom: 8px;
        }

        .stat-box .value {
            font-size: 36px;
            font-weight: 600;
            color: #e6edf3;
        }

        .stat-box-small {
            padding: 20px;
            background: #161b22;
            border-radius: 8px;
            min-width: 180px;
            text-align: left;
            flex: 1;
        }

        .stat-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 16px;
            color: #c9d1d9;
            padding: 8px 0;
        }
        
    </style>
    
    <div class="quiz-container">
        <div id="quizWrapper">
            <div class="quiz-header">
                <div class="question-counter" id="questionCounter"></div>
            </div>
            
            <div class="question-text" id="questionText"></div>
            
            <div class="options-container" id="optionsContainer"></div>
            
            <div class="explanation-box" id="explanationBox">
                <div class="explanation-title">✓ Right answer</div>
                <div class="explanation-text" id="explanationText"></div>
            </div>
            
            <div class="nav-buttons">
                <button class="quiz-btn btn-previous" id="prevBtn" onclick="previousQuestion()">Previous</button>
                <button class="quiz-btn btn-next" id="nextBtn" onclick="nextQuestion()">Next</button>
            </div>
        </div>

        <div class="results-container" id="resultsContainer">
            <div class="results-header">You did it! Quiz complete.</div>
            <div class="stats-container">
                <div class="stat-box">
                    <div class="label">Score</div>
                    <div class="value" id="scoreValue"></div>
                </div>
                <div class="stat-box">
                    <div class="label">Accuracy</div>
                    <div class="value" id="accuracyValue"></div>
                </div>
                <div class="stat-box-small">
                    <div class="stat-row">
                        <span class="label">Right</span>
                        <span class="value" id="rightValue"></span>
                    </div>
                    <div class="stat-row">
                        <span class="label">Wrong</span>
                        <span class="value" id="wrongValue"></span>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const quizData = """ + json.dumps(quiz_questions) + """;
        let currentQuestion = 0;
        let userAnswers = new Array(quizData.length).fill(null);
        
        const questionCounter = document.getElementById('questionCounter');
        const questionText = document.getElementById('questionText');
        const optionsContainer = document.getElementById('optionsContainer');
        const explanationBox = document.getElementById('explanationBox');
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const quizWrapper = document.getElementById('quizWrapper');
        const resultsContainer = document.getElementById('resultsContainer');
        
        function loadQuestion() {
            const q = quizData[currentQuestion];
            const hasAnswered = userAnswers[currentQuestion] !== null;

            questionCounter.textContent = `${currentQuestion + 1} / ${quizData.length}`;
            questionText.textContent = q.question;
            
            optionsContainer.innerHTML = '';
            explanationBox.classList.remove('show');
            
            const labels = ['A', 'B', 'C', 'D'];
            q.options.forEach((option, index) => {
                const optionDiv = document.createElement('div');
                optionDiv.className = 'option';
                
                if (!hasAnswered) {
                    optionDiv.onclick = () => selectOption(index);
                }
                
                optionDiv.innerHTML = `
                    <span class="option-label">${labels[index]}</span>
                    <span class="option-text">${option}</span>
                    <span class="option-icon"></span>
                `;
                
                optionsContainer.appendChild(optionDiv);
            });

            if (hasAnswered) {
                showAnswerFeedback(userAnswers[currentQuestion]);
            }
            
            updateButtons();
        }

        function showAnswerFeedback(selectedIndex) {
            const q = quizData[currentQuestion];
            const options = document.querySelectorAll('.option');

            options.forEach((opt, i) => {
                opt.classList.add('disabled');
                opt.onclick = null;
                
                if (i === q.correct_index) {
                    opt.classList.add('correct');
                    opt.querySelector('.option-icon').textContent = '✓';
                } else if (i === selectedIndex && i !== q.correct_index) {
                    opt.classList.add('wrong');
                    opt.querySelector('.option-icon').textContent = '✕';
                }
            });
            
            if (selectedIndex !== q.correct_index && options[selectedIndex]) {
                 options[selectedIndex].classList.add('selected');
            }

            const labels = ['A', 'B', 'C', 'D'];
            const correctLabel = labels[q.correct_index];
            
            explanationBox.innerHTML = `
                <div class="explanation-title">
                    ✓ Right answer
                    <span class="correct-option-label">Option ${correctLabel}</span>
                </div>
                <div class="explanation-text">${q.explanation}</div>
            `;
            
            explanationBox.classList.add('show');
        }
        
        function selectOption(index) {
            if (userAnswers[currentQuestion] !== null) return;
            userAnswers[currentQuestion] = index;
            showAnswerFeedback(index);
            updateButtons();
        }
        
        function nextQuestion() {
            if (currentQuestion < quizData.length - 1) {
                currentQuestion++;
                loadQuestion();
            }
        }
        
        function previousQuestion() {
            if (currentQuestion > 0) {
                currentQuestion--;
                loadQuestion();
            }
        }
        
        function updateButtons() {
            prevBtn.disabled = currentQuestion === 0;
            const isAnswered = userAnswers[currentQuestion] !== null;

            if (currentQuestion === quizData.length - 1) {
                nextBtn.textContent = 'Done';
                nextBtn.onclick = showResults;
                nextBtn.disabled = !isAnswered;
            } else {
                nextBtn.textContent = 'Next';
                nextBtn.onclick = nextQuestion;
                nextBtn.disabled = !isAnswered;
            }
        }

        function showResults() {
            let score = 0;
            for (let i = 0; i < quizData.length; i++) {
                if (userAnswers[i] === quizData[i].correct_index) {
                    score++;
                }
            }
            
            const wrong = quizData.length - score;
            const accuracy = quizData.length > 0 ? Math.round((score / quizData.length) * 100) : 0;

            document.getElementById('scoreValue').textContent = `${score} / ${quizData.length}`;
            document.getElementById('accuracyValue').textContent = `${accuracy}%`;
            document.getElementById('rightValue').textContent = score;
            document.getElementById('wrongValue').textContent = wrong;

            quizWrapper.style.display = 'none';
            resultsContainer.style.display = 'block';
        }
        
        loadQuestion();
    </script>
    """
    
    return html


def parse_flashcards(text):
    """Parse flashcard JSON from AI response"""
    try:
        json_match = re.search(r'\[[\s\S]*\]', text)
        if json_match:
            flashcards = json.loads(json_match.group())
            return flashcards
        return None
    except:
        return None


def parse_quiz(text):
    """Parse quiz JSON from AI response"""
    try:
        json_match = re.search(r'\[[\s\S]*\]', text)
        if json_match:
            quiz_data = json.loads(json_match.group())
            return quiz_data
        return None
    except:
        return None


# ------------------- CHAT UI + STREAMING OUTPUT -------------------

col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    prompt = st.text_area(
        label="Enter your topic or text", 
        placeholder="Paste your study material here...", 
        height=200, 
        label_visibility="collapsed"
    )
    generate_button = st.button("🚀 Generate", use_container_width=True)


if generate_button:
    st.session_state.last_learning_response = None
    if not prompt.strip():
        st.warning("⚠️ Please enter something first!")
    st.session_state.last_learning_response = None
    if not prompt.strip():
        st.warning("⚠️ Please enter something first!")
    else:
        formatted_prompt = format_message(mode, prompt, num_questions_local=num_questions)
        st.session_state.messages.append({"role": "user", "content": prompt})
        full_reply = ""
        with st.chat_message("assistant"):
            if mode == "Learning":
                placeholder = st.empty()
                for token in stream_llm(formatted_prompt):
                    full_reply += token
                    placeholder.write(full_reply + "▌")
                placeholder.write(full_reply) # Final write without cursor
                st.session_state.last_learning_response = full_reply

            elif mode == "Flashcards":
                with st.spinner("✨ Generating flashcards..."):
                    full_reply = "".join(stream_llm(formatted_prompt))
                    flashcards = parse_flashcards(full_reply)
                    if flashcards and len(flashcards) > 0:
                        st.session_state.flashcard_data = flashcards
                        html_content = generate_flashcard_html(flashcards)
                        st.components.v1.html(html_content, height=500, scrolling=False)
                    else:
                        st.error("Failed to generate flashcards. Please try again.")
                        st.write(full_reply)
            
            elif mode == "Quiz":
                with st.spinner(f"📝 Generating {num_questions} question quiz..."):
                    full_reply = "".join(stream_llm(formatted_prompt))
                    quiz_data = parse_quiz(full_reply)
                    if quiz_data and len(quiz_data) > 0:
                        st.session_state.quiz_data = quiz_data
                        html_content = generate_quiz_html(quiz_data)
                        st.components.v1.html(html_content, height=800, scrolling=False)
                    else:
                        st.error("Failed to generate quiz. Please try again.")
                        st.write(full_reply)

        if full_reply:
            st.session_state.messages.append({"role": "assistant", "content": full_reply})   
            
# Display contextual action buttons if a learning response exists
if mode == "Learning" and st.session_state.last_learning_response:
    st.markdown("---")
    st.markdown("##### Great! Now you can do this from this explanation:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✨ Create Flashcards"):
            with st.spinner("Generating flashcards from the text..."):
                flashcard_prompt = format_message(
                    mode_type="Flashcards", 
                    user_text="",
                    context=st.session_state.last_learning_response
                )
                
                full_reply = "".join(stream_llm(flashcard_prompt))
                flashcards = parse_flashcards(full_reply)
                
                if flashcards and len(flashcards) > 0:
                    st.session_state.flashcard_data = flashcards
                    html_content = generate_flashcard_html(flashcards)
                    st.components.v1.html(html_content, height=500, scrolling=False)
                else:
                    st.error("Could not generate flashcards from this text.")

    with col2:
        if st.button("📝 Generate Quiz"):
            with st.spinner("Generating a quiz from the text..."):
                quiz_prompt = format_message(
                    mode_type="Quiz",
                    user_text="",
                    num_questions_local=num_questions,
                    context=st.session_state.last_learning_response
                )
                
                full_reply = "".join(stream_llm(quiz_prompt))
                quiz_data = parse_quiz(full_reply)

                if quiz_data and len(quiz_data) > 0:
                    st.session_state.quiz_data = quiz_data
                    html_content = generate_quiz_html(quiz_data)
                    st.components.v1.html(html_content, height=800, scrolling=False)
                else:
                    st.error("Could not generate a quiz from this text.")



if st.sidebar.button("🗑️ Clear History"):
    st.session_state.messages = []
if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_learning_response" not in st.session_state:
    st.session_state.last_learning_response = None

if "current_flashcard" not in st.session_state:
    st.session_state.current_flashcard = 0
    st.rerun()

with st.sidebar.expander("📜 Chat History"):
    for i, msg in enumerate(st.session_state.messages):
        role = "You" if msg["role"] == "user" else "AI"
        content_preview = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
        st.text(f"{role}: {content_preview}")