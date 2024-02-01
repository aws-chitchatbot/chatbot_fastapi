import streamlit as st
from langchain_community.llms import CTransformers
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import PyPDFLoader
import re


def generate_poem(content):
    llm = CTransformers(
        model="TheBloke/Llama-2-7B-chat-GGUF",
        model_file="llama-2-7b-chat.Q5_K_M.gguf",
        model_type="llama",
    )

    prompt = ChatPromptTemplate.from_template(
        "Write me a poem about {content}. Poetry, also known as verse, is a form of literature that uses aesthetic and often rhythmic characteristics of language - e.g.: phonetics, sound symbolism - evoke meaning in addition to or instead of prosaic outward meaning. A literary work written by a poet using this principle."
    )
    chain = prompt | llm
    result = chain.invoke({"content": content})
    return result


def combine_sentences(sentences, buffer_size=1):
    # Go through each sentence dict
    for i in range(len(sentences)):
        # Create a string that will hold the sentences which are joined
        combined_sentence = ""

        # Add sentences before the current one, based on the buffer size.
        for j in range(i - buffer_size, i):
            # Check if the index j is not negative (to avoid index out of range like on the first one)
            if j >= 0:
                # Add the sentence at index j to the combined_sentence string
                combined_sentence += sentences[j]["sentence"] + " "

        # Add the current sentence
        combined_sentence += sentences[i]["sentence"]

        # Add sentences after the current one, based on the buffer size
        for j in range(i + 1, i + 1 + buffer_size):
            # Check if the index j is within the range of the sentences list
            if j < len(sentences):
                # Add the sentence at index j to the combined_sentence string
                combined_sentence += " " + sentences[j]["sentence"]

        # Then add the whole thing to your dict
        # Store the combined sentence in the current sentence dict
        sentences[i]["combined_sentence"] = combined_sentence

    return sentences


def main():
    st.title("인공지능 시인")

    content = st.text_input("시의 주제를 제시해주세요.")

    if st.button("시 작성 요청하기"):
        with st.spinner("시 작성 중..."):
            poem_result = generate_poem(content)
            st.write(poem_result)


if __name__ == "__main__":
    with open("./test.txt") as file:
        essay = file.read()

    # Splitting the essay on '.', '?', and '!'
    single_sentences_list = re.split(r"(?<=[.?!])\s+", essay)
    print(f"{len(single_sentences_list)} senteneces were found")
    sentences = [
        {"sentence": x, "index": i} for i, x in enumerate(single_sentences_list)
    ]
    print(sentences[:3])
    print("-------------")
    sentences = combine_sentences(sentences)
    print(sentences[:3])
