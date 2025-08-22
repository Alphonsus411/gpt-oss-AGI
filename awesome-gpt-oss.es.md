![gpt-oss](./docs/gpt-oss.svg)

# Lista genial de gpt-oss

Esta es una lista de guías y recursos para ayudarte a comenzar con los modelos gpt-oss.

- [Inferencia](#inference)
  - [Local](#local)
  - [Servidor](#server)
  - [Nube](#cloud)
- [Ejemplos / Tutoriales](#examples--tutorials)
- [Herramientas](#tools)

<a id="inference"></a>
## Inferencia

### Local

- Ollama
  - [Cómo ejecutar gpt-oss localmente con Ollama](https://cookbook.openai.com/articles/gpt-oss/run-locally-ollama)
  - [Entrada de blog del lanzamiento de Ollama y gpt-oss](https://ollama.com/blog/gpt-oss)
  - [Explora los modelos en Ollama](https://ollama.com/library/gpt-oss)
- LM Studio
  - [Entrada de blog del lanzamiento de LM Studio y gpt-oss](https://lmstudio.ai/blog/gpt-oss)
  - [Usa gpt-oss-20b con LM Studio](https://lmstudio.ai/models/openai/gpt-oss-20b)
  - [Usa gpt-oss-120b con LM Studio](https://lmstudio.ai/models/openai/gpt-oss-120b)
- Hugging Face y Transformers
  - [Cómo ejecutar gpt-oss con Transformers](https://cookbook.openai.com/articles/gpt-oss/run-transformers)
  - [Entrada de blog del lanzamiento de Hugging Face y gpt-oss](https://huggingface.co/blog/welcome-openai-gpt-oss)
  - [Colección de ejemplos de Hugging Face](https://github.com/huggingface/gpt-oss-recipes)
- NVIDIA
  - [gpt-oss en RTX](https://blogs.nvidia.com/blog/rtx-ai-garage-openai-oss)
- AMD
  - [Ejecución de modelos gpt-oss en procesadores AMD Ryzen AI y tarjetas gráficas Radeon](https://www.amd.com/en/blogs/2025/how-to-run-openai-gpt-oss-20b-120b-models-on-amd-ryzen-ai-radeon.html)

<a id="server"></a>
### Servidor

- vLLM
  - [Cómo ejecutar gpt-oss con vLLM](https://cookbook.openai.com/articles/gpt-oss/run-vllm)
- NVIDIA
  - [Optimización de gpt-oss con NVIDIA TensorRT-LLM](https://cookbook.openai.com/articles/run-nvidia)
  - [Implementación de gpt-oss en TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM/blob/main/docs/source/blogs/tech_blog/blog9_Deploying_GPT_OSS_on_TRTLLM.md)
- AMD
  - [Ejecutar los últimos modelos abiertos de OpenAI en hardware de IA de AMD](https://rocm.blogs.amd.com/ecosystems-and-partners/openai-day-0/README.html)

<a id="cloud"></a>
### Nube

- Groq
  - [Entrada de blog del lanzamiento de Groq y gpt-oss](https://groq.com/blog/day-zero-support-for-openai-open-models)
  - [Modelo gpt-oss-120b en el Playground de GroqCloud](https://console.groq.com/playground?model=openai/gpt-oss-120b)
  - [Modelo gpt-oss-20b en el Playground de GroqCloud](https://console.groq.com/playground?model=openai/gpt-oss-20b)
  - [gpt-oss con búsqueda web integrada en GroqCloud](https://console.groq.com/docs/browser-search)
  - [gpt-oss con ejecución de código integrada en GroqCloud](https://console.groq.com/docs/code-execution)
  - [API de respuestas en Groq](https://console.groq.com/docs/responses-api)
- NVIDIA
  - [Entrada de blog del lanzamiento de NVIDIA](https://blogs.nvidia.com/blog/openai-gpt-oss/)
  - [Entrada de blog del lanzamiento para desarrolladores de NVIDIA y gpt-oss](https://developer.nvidia.com/blog/delivering-1-5-m-tps-inference-on-nvidia-gb200-nvl72-nvidia-accelerates-openai-gpt-oss-models-from-cloud-to-edge/)
  - Usa [gpt-oss-120b](https://build.nvidia.com/openai/gpt-oss-120b) y [gpt-oss-20b](https://build.nvidia.com/openai/gpt-oss-20b) en la nube de NVIDIA
- Cloudflare
  - [Entrada de blog del lanzamiento de Cloudflare y gpt-oss](http://blog.cloudflare.com/openai-gpt-oss-on-workers-ai)
  - [gpt-oss-120b en Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/models/gpt-oss-120b)
  - [gpt-oss-20b en Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/models/gpt-oss-20b)
- AMD
  - [gpt-oss-120B en AMD MI300X](https://huggingface.co/spaces/amd/gpt-oss-120b-chatbot)

<a id="examples--tutorials"></a>
## Ejemplos y tutoriales

- [Formato de respuesta de OpenAI harmony](https://cookbook.openai.com/articles/openai-harmony)

<a id="tools"></a>
## Herramientas

- [Ejemplo de herramienta `python` para gpt-oss](./gpt_oss/tools/python_docker/)
- [Ejemplo de herramienta `browser` para gpt-oss](./gpt_oss/tools/simple_browser/)

## Contribuciones

Siéntete libre de abrir un PR para añadir tus propias guías y recursos sobre cómo ejecutar gpt-oss. Intentaremos revisarlo y añadirlo aquí.
