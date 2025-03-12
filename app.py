import streamlit as st
import re
import json
import os
from google import genai
from google.genai import types

# Функция для извлечения JSON из ответа модели
def extract_code_json(markdown_string):
    matches = re.compile(r'```(?:json)?\n(.*?)\n```', re.DOTALL).findall(markdown_string)
    multi_line_matches = [match.strip() for match in matches if "\n" in match.strip()]
    json_str = "\n\n".join(multi_line_matches)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            # Попробуем исправить некоторые распространенные ошибки в JSON
            json_str = json_str.replace("'", '"')
            return json.loads(json_str)
        except:
            st.error("Ошибка при обработке ответа модели")
            return []

# Класс для работы с API Gemini
class APIEasy:
    def __init__(self, api_key, temperature=0, top_p=1, seed=42):
        self.client = genai.Client(api_key=api_key)
        self.config_model = types.GenerateContentConfig(
            temperature=temperature,
            top_p=top_p,
            seed=seed,
        )

    def send_message(self, prompt):
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt, 
                config=self.config_model
            )
            return response.text
        except Exception as e:
            st.error(f"Ошибка при обращении к API: {str(e)}")
            return ""

# Настройка страницы
st.set_page_config(
    page_title="Упражнения по русскому языку",
    page_icon="📚",
    layout="wide"
)

# Заголовок приложения
st.title("Упражнения по русскому языку")

# Боковая панель для ввода API ключа
with st.sidebar:
    st.header("Настройки")
    api_key = st.text_input("Введите API ключ Gemini:", type="password")
    st.markdown("---")
    st.markdown("Приложение для генерации и проверки упражнений по русскому языку")

# Основная часть приложения
if not api_key:
    st.warning("Пожалуйста, введите API ключ Gemini в боковой панели")
else:
    # Инициализация API
    api = APIEasy(api_key=api_key)
    
    # Ввод темы для упражнений
    st.subheader("Создание упражнений")
    
    # Примеры тем
    st.markdown("""
    **Примеры тем:**
    - н и нн в причастиях
    - Правописание приставок пре- и при-
    - Правописание безударных гласных в корне
    - Правописание -тся и -ться в глаголах
    - Знаки препинания в сложном предложении
    """)
    
    # Поле для ввода темы
    theme = st.text_input("Введите тему для упражнений:", value="н и нн в причастиях")
    
    # Шаблон промта
    prompt_template = """Ты - учитель русского языка.

** Требования ** 
1) Одно упражнение - одно предложение
2) В каждом предложении должен быть пропуск, обозначенный многоточием (...)
3) Пропуск должен быть на месте, где нужно вставить правильную букву или буквы
4) Создай 5 упражнений

** Формат ответа пример **
В Json
[
    {"упражнение": "Варе...ый картофель был очень вкусным.", "ответ": "нн"},
    {"упражнение": "Краше...ый пол блестел в лучах солнца.", "ответ": "н"},
    {"упражнение": "...", "ответ": "..."},
    {"упражнение": "...", "ответ": "..."},
    {"упражнение": "...", "ответ": "..."}
]
"""
    prompt_template1 = """** Тема **
    {theme}
    """
    
    # Формирование промта с выбранной темой
    prompt = prompt_template1.format(theme=theme)
    prompt = prompt_template + prompt
    
    # Показать промт (скрыто по умолчанию)
    with st.expander("Показать полный промт"):
        st.text_area("Промт для генерации:", value=prompt, height=300, disabled=True)
    
    if st.button("Сгенерировать упражнения"):
        with st.spinner("Генерация упражнений..."):
            response = api.send_message(prompt)
            if response:
                exercises = extract_code_json(response)
                if exercises and isinstance(exercises, list):
                    # Сохраняем упражнения в session_state
                    st.session_state.exercises = exercises
                    st.session_state.user_answers = [""] * len(exercises)
                    st.success(f"Сгенерировано {len(exercises)} упражнений!")
                else:
                    st.error("Не удалось получить упражнения в правильном формате")
    
    # Отображение упражнений и ввод ответов
    if 'exercises' in st.session_state and st.session_state.exercises:
        st.subheader("Упражнения")
        
        for i, exercise in enumerate(st.session_state.exercises):
            col1, col2 = st.columns([3, 1])
            
            # Получаем текст упражнения и заменяем многоточие на поле ввода
            exercise_text = exercise.get("упражнение", "")
            
            with col1:
                st.markdown(f"**{i+1}. {exercise_text}**")
            
            with col2:
                # Поле для ввода ответа
                st.session_state.user_answers[i] = st.text_input(
                    f"Ответ {i+1}", 
                    key=f"answer_{i}",
                    value=st.session_state.user_answers[i] if 'user_answers' in st.session_state else ""
                )
        
        # Кнопка проверки
        if st.button("Проверить ответы"):
            st.subheader("Результаты")
            
            correct_count = 0
            
            for i, exercise in enumerate(st.session_state.exercises):
                user_answer = st.session_state.user_answers[i].strip()
                correct_answer = exercise.get("ответ", "").strip()
                
                if user_answer.lower() == correct_answer.lower():
                    st.success(f"{i+1}. Правильно! Ответ: {correct_answer}")
                    correct_count += 1
                else:
                    st.error(f"{i+1}. Неправильно. Ваш ответ: {user_answer}, Правильный ответ: {correct_answer}")
            
            # Итоговый результат
            st.markdown(f"### Итог: {correct_count} из {len(st.session_state.exercises)} правильных ответов")
            percentage = (correct_count / len(st.session_state.exercises)) * 100
            st.progress(percentage / 100)
            
            if percentage == 100:
                st.balloons()
                st.markdown("## 🎉 Отлично! Все ответы правильные!")
            elif percentage >= 70:
                st.markdown("## 👍 Хороший результат!")
            else:
                st.markdown("## 📚 Продолжайте практиковаться!") 