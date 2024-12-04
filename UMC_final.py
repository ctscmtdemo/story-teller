import streamlit as st
import PyPDF2
import google.generativeai as genai
from googletrans import Translator, LANGUAGES
from PIL import Image
from gtts import gTTS
import os
import tempfile

# Configure the API key
my_secret = os.environ['GOOGLE_API_KEY']
genai.configure(api_key=my_secret)

# Define the model
model = genai.GenerativeModel('gemini-1.5-flash')


def extract_text_from_pdf(pdf_file):
    text = ""
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text


def translate_text(text, dest_language):
    translator = Translator()
    if dest_language not in LANGUAGES:
        raise ValueError(f"Invalid destination language: {dest_language}")
    translation = translator.translate(text, dest=dest_language)
    return translation.text


def generate_speech_from_text(text, language, output_format='mp3'):
    translated_text = translate_text(text, language)
    tts = gTTS(text=translated_text, lang=language, slow=False)
    with tempfile.NamedTemporaryFile(delete=False,
                                     suffix=f".{output_format}") as f:
        tts.save(f.name)
        return f.name


def generate_content(text):
    try:
        response = model.generate_content([
            "The provided text snippet comes from a PDF document. The extracted content. Please analyze the provided text and generate a summary. markdown text is NOT ALLOWED in output. Remove all asterisks from a text string",
            text
        ],
                                          stream=True)
        response.resolve()
        # Remove asterisks from the generated content
        cleaned_text = response.text.replace('*',
                                             '') if response.text else None
        return cleaned_text
    except Exception as e:
        st.error(f"Error generating content: {e}")
        return None


def generate_caption(image_file):
    try:
        # Load the image from the file
        image = Image.open(image_file)

        # Generate a caption based on the image
        response = model.generate_content([
            "Generate a descriptive caption for the following image in one line with should be not more than 5 words.",
            image
        ])
        text_output = response.candidates[0].content
        return text_output.parts[0].text if text_output else None
    except Exception as e:
        st.error(f"Error generating caption: {e}")
        return None


def generate_response(prompt, image_file):
    try:
        # Load the image from the file
        image = Image.open(image_file)

        # Generate content based on the prompt and image
        response = model.generate_content([prompt, image])
        text_output = response.candidates[0].content
        return text_output.parts[0].text if text_output else None
    except Exception as e:
        st.error(f"Error generating response: {e}")
        return None


def main():
    st.title("Unified Media Converter: PDF/Image to Audiobook")

    uploaded_file = st.file_uploader("Choose a PDF or Image file",
                                     type=["pdf", "jpg", "jpeg", "png"])

    if uploaded_file is not None:
        file_type = uploaded_file.type

        if file_type == "application/pdf":
            st.subheader("PDF Processing")
            text = extract_text_from_pdf(uploaded_file)
            if text:
                generated_content = generate_content(text)
                if generated_content:
                    st.subheader("Generated Content")
                    st.text_area("Generated Content",
                                 generated_content,
                                 height=200)

                    st.subheader("Convert PDF Content to Speech")
                    language = st.selectbox(
                        "Select language for translation:",
                        [(code, name) for code, name in LANGUAGES.items()])
                    selected_language_code = language[0]
                    output_format = st.selectbox("Select output format:",
                                                 ['mp3', 'wav'])

                    if st.button("Generate Speech"):
                        try:
                            output_file = generate_speech_from_text(
                                generated_content, selected_language_code,
                                output_format)
                            st.success(
                                f"Audio content written to file '{output_file}'"
                            )
                            st.audio(output_file,
                                     format=f"audio/{output_format}")

                            with open(output_file, "rb") as file:
                                st.download_button(
                                    label="Download audio file",
                                    data=file,
                                    file_name=output_file,
                                    mime=f"audio/{output_format}")

                            os.remove(output_file)
                        except Exception as e:
                            st.error(f"Error generating speech: {e}")
                else:
                    st.error("No content available to convert.")
            else:
                st.error("No text extracted from PDF.")

        elif file_type in ["image/jpeg", "image/png"]:
            st.subheader("Image Processing")
            img = Image.open(uploaded_file)
            option = st.selectbox("Select action:",
                                  ["Storytelling with Caption", "Q&A"])

            if option == "Storytelling with Caption":
                caption = generate_caption(uploaded_file)
                if caption:
                    st.image(img, caption='Uploaded Image.', width=300)
                    st.subheader("Generated Caption")
                    st.write(caption)

                    narrative_context = generate_response(
                        "Describe the input image in a storytelling format. Tell a story inspired by its details. Use vivid descriptions and creative interpretations to bring the scene to life.",
                        uploaded_file)
                    if narrative_context:
                        st.subheader("Generated Story")
                        st.write(narrative_context)

                        st.subheader("Convert Story to Speech")
                        language = st.selectbox(
                            "Select language for translation:",
                            [(code, name) for code, name in LANGUAGES.items()])
                        selected_language_code = language[0]
                        output_format = st.selectbox("Select output format:",
                                                     ['mp3', 'wav'])

                        if st.button("Generate Speech"):
                            try:
                                output_file = generate_speech_from_text(
                                    narrative_context, selected_language_code,
                                    output_format)
                                st.success(
                                    f"Audio content written to file '{output_file}'"
                                )
                                st.audio(output_file,
                                         format=f"audio/{output_format}")

                                with open(output_file, "rb") as file:
                                    st.download_button(
                                        label="Download audio file",
                                        data=file,
                                        file_name=output_file,
                                        mime=f"audio/{output_format}")

                                os.remove(output_file)
                            except Exception as e:
                                st.error(f"Error generating speech: {e}")

            elif option == "Q&A":
                st.header("Your Question")
                question = st.text_area(label="Enter your question")
                submit = st.button("Submit")

                if submit:
                    response = generate_response(question, uploaded_file)
                    if response:
                        st.subheader("Generated Response")
                        st.write(response)
                    else:
                        st.error("Error generating response.")

        else:
            st.error(
                "Unsupported file type. Please upload a PDF or image file.")


if __name__ == "__main__":
    main()
