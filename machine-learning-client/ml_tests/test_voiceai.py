import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from voiceai import run_prompt, save_to_db, voice_input, gpt_call
import speech_recognition as sr


@patch("voiceai.gpt_call", new_callable=AsyncMock)
def test_run_prompt_with_mock(mock_gpt_call):
    mock_gpt_call.return_value = "This is a test summary."
    text = "This is a transcription"
    result = asyncio.run(run_prompt(text))
    assert result == "This is a test summary."
    mock_gpt_call.assert_awaited_once()


@patch("voiceai.pymongo.MongoClient")
def test_db_save(mock_mongo_client):
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_mongo_client.return_value.__getitem__.return_value = mock_db
    transcription = "Hello world"
    summary = "A summary of Hello world"
    save_to_db(transcription, summary)
    mock_collection.insert_one.assert_called_once()
    doc = mock_collection.insert_one.call_args[0][0]
    assert doc["transcript"] == transcription
    assert doc["summary"] == summary
    assert "timestamp" in doc


@patch("voiceai.sr.Recognizer.adjust_for_ambient_noise")
@patch("voiceai.sr.Recognizer.recognize_google")
@patch("voiceai.sr.Recognizer.listen")
@patch("voiceai.sr.Microphone")
def test_voice_input_basic(
    mock_mic, mock_listen, mock_recognize_google, mock_adjustment_noise
):
    mock_recognize_google.side_effect = [
        "Hello there",
        "Shaurya Srivastava",
        "James",
        "end",
    ]
    mock_listen.return_value = MagicMock()
    result = voice_input()
    assert "hello there" in result.lower()
    assert "shaurya srivastava" in result.lower()
    assert "james" in result.lower()
    assert "end" in result.lower()
    assert isinstance(result, str)
    mock_recognize_google.assert_called()


@patch("voiceai.sr.Recognizer.adjust_for_ambient_noise")
@patch("voiceai.sr.Recognizer.recognize_google")
@patch("voiceai.sr.Recognizer.listen")
@patch("voiceai.sr.Microphone")
def test_voice_input_basic_two(
    mock_mic, mock_listen, mock_recognize_google, mock_adjustment_noise
):
    mock_recognize_google.side_effect = [
        "Hello there",
        "Shaurya Srivastava",
        "end",
        "James",
    ]
    mock_listen.return_value = MagicMock()
    result = voice_input()
    assert "hello there" in result.lower()
    assert "shaurya srivastava" in result.lower()
    assert "james" not in result.lower()
    assert "end" in result.lower()
    assert isinstance(result, str)
    mock_recognize_google.assert_called()


@patch("aiohttp.ClientSession.post")
def test_gpt_call_mock_response(mock_post):

    mock_response = AsyncMock()
    mock_response.json = AsyncMock(
        return_value={"choices": [{"message": {"content": "Mocked GPT summary"}}]}
    )
    mock_post.return_value.__aenter__.return_value = mock_response

    result = asyncio.run(gpt_call("Test input", "Prompt: {text}"))
    assert result == "Mocked GPT summary"


@patch("voiceai.sr.Recognizer.adjust_for_ambient_noise")
@patch("voiceai.sr.Recognizer.recognize_google", side_effect=sr.UnknownValueError)
@patch("voiceai.sr.Recognizer.listen")
@patch("voiceai.sr.Microphone")
def test_voice_input_handles_unknown_value(
    mock_mic, mock_listen, mock_recognize_google, mock_adjustment_noise
):
    mock_listen.return_value = MagicMock()

    with patch(
        "voiceai.sr.Recognizer.recognize_google",
        side_effect=[sr.UnknownValueError, "end"],
    ):
        result = voice_input()
        assert isinstance(result, str)


@patch("voiceai.sr.Recognizer.adjust_for_ambient_noise")
@patch(
    "voiceai.sr.Recognizer.recognize_google", side_effect=sr.RequestError("API down")
)
@patch("voiceai.sr.Recognizer.listen")
@patch("voiceai.sr.Microphone")
def test_voice_input_handles_request_error(
    mock_mic, mock_listen, mock_recognize_google, mock_adjustment_noise
):
    mock_listen.return_value = MagicMock()

    with patch(
        "voiceai.sr.Recognizer.recognize_google",
        side_effect=[sr.RequestError("API fail"), "end"],
    ):
        result = voice_input()
        assert isinstance(result, str)
