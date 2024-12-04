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
            "The provided text snippet comes from a PDF document. The extracted content, Please analyze the provided text and generate insights that can help in understanding the information it contains. markdown text is NOT ALLOWED in output.Remove all asterisks from a text string",
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


# Main function to run the Streamlit app
def main():
    # Streamlit app title
    st.title("Unified Media Converter: Image/PDF to Audiobook")

    # Upload a file
    uploaded_file = st.file_uploader("Choose a PDF or Image file",
                                     type=["pdf", "jpg", "jpeg", "png"])

    if uploaded_file is not None:
        file_type = uploaded_file.type

        if file_type == "application/pdf":
            text = extract_text_from_pdf(uploaded_file)

            generated_content = generate_content(text)
            if generated_content:
                st.subheader("Generated Content")
                st.text_area("Generated Content",
                             generated_content,
                             height=200)

                # Text-to-Speech section
                st.subheader("Convert Content to Speech")
                language = st.selectbox("Select language for translation:",
                                        [(code, name)
                                         for code, name in LANGUAGES.items()])
                selected_language_code = language[0]
                output_format = st.selectbox("Select output format:",
                                             ['mp3', 'wav'])

                if st.button("Generate Speech"):
                    try:
                        output_file = generate_speech_from_text(
                            generated_content, selected_language_code,
                            output_format)
                        st.success(
                            f"Audio content written to file '{output_file}'")
                        st.audio(output_file, format=f"audio/{output_format}")

                        # Provide a download link for the file
                        with open(output_file, "rb") as file:
                            st.download_button(label="Download audio file",
                                               data=file,
                                               file_name=output_file,
                                               mime=f"audio/{output_format}")

                        # Remove the file after download link is generated
                        os.remove(output_file)
                    except Exception as e:
                        st.error(f"Error generating speech: {e}")
            else:
                st.error("No content available to convert.")
        elif file_type in ["image/jpeg", "image/png"]:
            img = Image.open(uploaded_file)

            narrative_context = model.generate_content(img)
            narrative_context.resolve()

            response = model.generate_content(
                f"You are a caption of the image with a maximum of 10 words using the following scenario: {narrative_context}",
                stream=True)
            response.resolve()

            cap_col1, cap_col2 = st.columns([1, 1])

            with cap_col1:
                st.image(img, caption='Uploaded Image.', width=300)

            with cap_col2:
                st.subheader("Generated Caption")
                st.write(response.text)

            # Clean the narrative context text
            cleaned_narrative_text = narrative_context.text.replace('*', '')

            st.subheader("Generated Story")
            st.write(cleaned_narrative_text)

            st.subheader("Convert Story to Speech")
            language = st.selectbox("Select language for translation:",
                                    [(code, name)
                                     for code, name in LANGUAGES.items()])
            selected_language_code = language[0]
            output_format = st.selectbox("Select output format:",
                                         ['mp3', 'wav'])

            if st.button("Generate Speech"):
                try:
                    output_file = generate_speech_from_text(
                        cleaned_narrative_text, selected_language_code,
                        output_format)
                    st.success(
                        f"Audio content written to file '{output_file}'")
                    st.audio(output_file, format=f"audio/{output_format}")

                    with open(output_file, "rb") as file:
                        st.download_button(label="Download audio file",
                                           data=file,
                                           file_name=output_file,
                                           mime=f"audio/{output_format}")

                    os.remove(output_file)
                except Exception as e:
                    st.error(f"Error generating speech: {e}")
        else:
            st.error(
                "Unsupported file type. Please upload a PDF or image file.")


if __name__ == "__main__":
    main()
