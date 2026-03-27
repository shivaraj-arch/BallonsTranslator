from .base import *
from deep_translator import GoogleTranslator as DeepTranslatorGoogleTranslator
import requests
import json
import html # For html.unescape


# --- exceptions ---
class ProviderError(Exception):
    pass


class TranslateError(ProviderError):
    pass


# --- Constants for Google Translate ---
USER_AGENT_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
# Use the API key from your example as a constant
from config.secrets import GOOGLE_API_KEY
GOOGLE_API_URL_BASE = "https://translate-pa.googleapis.com/v1"  # Base API URL


class GoogleTranslateProviderPython:
    """
    Провайдер для взаимодействия с неофициальным Google Translate API (translateHtml).
    Использует предопределенный API ключ.
    """

    api_url_path_segment = "/translateHtml"  # Path to the translation endpoint

    def __init__(self, timeout: int = 10):
        self.base_headers = {
            "X-Goog-API-Key": GOOGLE_API_KEY,  # Use the constant
            "Content-Type": "application/json+protobuf",
            "User-Agent": USER_AGENT_BROWSER,
        }
        self.fetch_opts = {"timeout": timeout}
        self.requests_session = requests.Session()
        self.requests_session.headers.update(self.base_headers)

    def _request(self, method: str = "POST", json_payload: Dict = None):
        actual_url = f"{GOOGLE_API_URL_BASE}{self.api_url_path_segment}"

        try:
            response = self.requests_session.request(
                method, actual_url, json=json_payload, **self.fetch_opts
            )

            if response.status_code >= 400:
                message = response.reason
                try:
                    error_data = response.json()
                    if "error" in error_data and isinstance(error_data["error"], dict):
                        message = error_data["error"].get("message", response.reason)
                except json.JSONDecodeError:
                    pass  # Using response.reason
                raise ProviderError(f"HTTP {response.status_code}: {message}")

            response_data = response.json()

            if isinstance(response_data, dict) and "error" in response_data:
                error_details = response_data.get("error")
                msg = "API error"
                if isinstance(error_details, dict) and "message" in error_details:
                    msg = error_details["message"]
                raise ProviderError(msg)
            return response_data
        except requests.exceptions.RequestException as e:
            raise ProviderError(f"Request failed: {e}")
        except json.JSONDecodeError:
            raw_text = (
                response.text[:200]
                if response and hasattr(response, "text")
                else "NoResponseObject"
            )
            raise ProviderError(f"Failed to decode JSON. Raw: {raw_text}")

    def translate(
        self, text_list: List[str], target_language: str, source_language: str = "auto"
    ) -> Dict[str, any]:
        """
        Переводит список текстов.
        source_language: 'auto' или код языка (например, 'en')
        target_language: код языка (например, 'ru')
        """
        if not text_list:
            return {"lang": target_language, "translations": []}

        translations_result = []
        for text_item in text_list:
            if not text_item or not text_item.strip():
                translations_result.append("")
                continue

            payload = [[[text_item], source_language, target_language], "wt_lib"]

            try:
                response_data = self._request(method="POST", json_payload=payload)

                extracted_text = None
                if (
                    response_data
                    and isinstance(response_data, list)
                    and len(response_data) > 0
                ):
                    if isinstance(response_data[0], list) and len(response_data[0]) > 0:
                        first_inner_item = response_data[0][0]
                        if isinstance(first_inner_item, str):
                            extracted_text = first_inner_item
                        elif (
                            isinstance(first_inner_item, list)
                            and len(first_inner_item) > 0
                            and isinstance(first_inner_item[0], str)
                        ):
                            extracted_text = first_inner_item[0]

                if extracted_text:
                    translations_result.append(html.unescape(extracted_text))
                else:
                    translations_result.append("")
            except ProviderError:
                translations_result.append("")

        return {"lang": target_language, "translations": translations_result}


@register_translator("google")
class TransGoogle(BaseTranslator):

    concate_text = False
    default_fallback_name = "deep-translator"
    params: Dict = {
        "delay": 0.0,
    }

    def _setup_translator(self):
        self.internal_google_translator = GoogleTranslateProviderPython()

        self.lang_map["Auto"] = "auto"
        self.lang_map["简体中文"] = "zh-CN"
        self.lang_map["繁體中文"] = "zh-TW"
        self.lang_map["日本語"] = "ja"
        self.lang_map["English"] = "en"
        self.lang_map["한국어"] = "ko"
        self.lang_map["Tiếng Việt"] = "vi"
        self.lang_map["čeština"] = "cs"
        self.lang_map["Nederlands"] = "nl"
        self.lang_map["Français"] = "fr"
        self.lang_map["Deutsch"] = "de"
        self.lang_map["magyar nyelv"] = "hu"
        self.lang_map["Italiano"] = "it"
        self.lang_map["Polski"] = "pl"
        self.lang_map["Português"] = "pt"
        self.lang_map["limba română"] = "ro"
        self.lang_map["русский язык"] = "ru"
        self.lang_map["Español"] = "es"
        self.lang_map["Türk dili"] = "tr"
        self.lang_map["украї́нська мо́ва"] = "uk"
        self.lang_map["Thai"] = "th"
        self.lang_map["Arabic"] = "ar"
        self.lang_map["Hindi"] = "hi"
        self.lang_map["Malayalam"] = "ml"
        self.lang_map["Tamil"] = "ta"

        # Additional languages
        self.lang_map["Afrikaans"] = "af"
        self.lang_map["Albanian"] = "sq"
        self.lang_map["Amharic"] = "am"
        self.lang_map["Armenian"] = "hy"
        self.lang_map["Azerbaijani"] = "az"
        self.lang_map["Basque"] = "eu"
        self.lang_map["Belarusian"] = "be"
        self.lang_map["Bengali"] = "bn"
        self.lang_map["Bosnian"] = "bs"
        self.lang_map["Bulgarian"] = "bg"
        self.lang_map["Catalan"] = "ca"
        self.lang_map["Cebuano"] = "ceb"
        self.lang_map["Chichewa"] = "ny"
        self.lang_map["Corsican"] = "co"
        self.lang_map["Croatian"] = "hr"
        self.lang_map["Danish"] = "da"
        self.lang_map["Divehi"] = "dv"
        self.lang_map["Dutch"] = "nl"
        self.lang_map["Esperanto"] = "eo"
        self.lang_map["Estonian"] = "et"
        self.lang_map["Ewe"] = "ee"
        self.lang_map["Faroese"] = "fo"
        self.lang_map["Filipino"] = "fil"
        self.lang_map["Finnish"] = "fi"
        self.lang_map["Frisian"] = "fy"
        self.lang_map["Fulani"] = "ff"
        self.lang_map["Galician"] = "gl"
        self.lang_map["Georgian"] = "ka"
        self.lang_map["Greek"] = "el"
        self.lang_map["Gujarati"] = "gu"
        self.lang_map["Haitian Creole"] = "ht"
        self.lang_map["Hausa"] = "ha"
        self.lang_map["Hebrew"] = "he"
        self.lang_map["Hmong"] = "hmn"
        self.lang_map["Igbo"] = "ig"
        self.lang_map["Indonesian"] = "id"
        self.lang_map["Irish"] = "ga"
        self.lang_map["Javanese"] = "jw"
        self.lang_map["Kannada"] = "kn"
        self.lang_map["Kazakh"] = "kk"
        self.lang_map["Khmer"] = "km"
        self.lang_map["Kinyarwanda"] = "rw"
        self.lang_map["Kyrgyz"] = "ky"
        self.lang_map["Lao"] = "lo"
        self.lang_map["Latin"] = "la"
        self.lang_map["Latvian"] = "lv"
        self.lang_map["Lithuanian"] = "lt"
        self.lang_map["Luxembourgish"] = "lb"
        self.lang_map["Macedonian"] = "mk"

    def _translate_with_private_api_fallback(self, src_list: List[str], reason: str) -> List[str]:
        source_lang_code = self.lang_map.get(self.lang_source, "auto")
        target_lang_code = self.lang_map.get(self.lang_target, "en")

        LOGGER.warning(
            "deep-translator failed (%s). Falling back to Google private API for %s -> %s.",
            reason,
            self.lang_source,
            self.lang_target,
        )

        response_data = self.internal_google_translator.translate(
            src_list,
            target_language=target_lang_code,
            source_language=source_lang_code,
        )

        if response_data and isinstance(response_data.get("translations"), list):
            translated_texts = response_data["translations"]
            if len(translated_texts) == len(src_list):
                LOGGER.info(
                    "Google private API fallback completed for %s text block(s).",
                    len(src_list),
                )
                return translated_texts

        LOGGER.error(
            "Google private API fallback returned an invalid response for %s text block(s).",
            len(src_list),
        )
        return [""] * len(src_list)
    
    def _translate(self, src_list: List[str]) -> List[str]:
        if not src_list:
            return []

        try:
            source_lang_code = self.lang_map.get(self.lang_source, "auto")
            target_lang_code = self.lang_map.get(self.lang_target, "en")
            translated_texts = []
            translator = DeepTranslatorGoogleTranslator(
                source=source_lang_code,
                target=target_lang_code,
            )
            for text_item in src_list:
                if not text_item or not text_item.strip():
                    translated_texts.append("")
                    continue
                translated_texts.append(translator.translate(text_item))

            LOGGER.info(
                "Primary translator %s completed for %s text block(s).",
                self.default_fallback_name,
                len(src_list),
            )
            return translated_texts

        except Exception as e:
            LOGGER.warning("Primary translator %s failed: %s", self.default_fallback_name, e)
            try:
                return self._translate_with_private_api_fallback(src_list, str(e))
            except ProviderError as fallback_error:
                LOGGER.error("Google private API fallback failed: %s", fallback_error)
                return [""] * len(src_list)
            except Exception as fallback_error:
                LOGGER.error("Unexpected error in Google private API fallback: %s", fallback_error)
                return [""] * len(src_list)
