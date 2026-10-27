# Models
- gemini-3.8-flash 支持 [Gemini Official Format, OpenAI Chat Completions (Image analysis)]
- gemini-3.7-flash 支持 [Gemini Official Format, OpenAI Chat Completions (Image analysis)]

# Base URL
请求基址为 `https://ai.t8star.org`。`{{YOUR_API_KEY}}`、`{{MODEL}}`、`{{PROMPT}}` 使用前需替换；各节分别列明允许的模型。Python `http.client` 使用 `HTTPSConnection("ai.t8star.org")` 加相对请求路径。所有真实响应中的图片 URL / Base64 与不透明签名已脱敏，占位符不能用于下载或解码。

# Gemini Official Format

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /v1beta/models/{model}:generateContent:
    post:
      summary: Gemini Official Format
      deprecated: false
      description: Gemini Official Format。路径中的 model 替换为所选模型名；generationConfig 及所列嵌套配置均非必填。
      tags:
      - 聊天(Chat)/Gemini Official Format
      parameters:
      - name: model
        in: path
        required: true
        description: 将当前受支持的模型名放入路径。
        schema:
          type: string
          enum:
          - gemini-3.8-flash
          - gemini-3.7-flash
      - name: Content-Type
        in: header
        description: ''
        required: true
        example: application/json
        schema:
          type: string
      - name: Authorization
        in: header
        description: ''
        required: false
        example: Bearer {{YOUR_API_KEY}}
        schema:
          type: string
          default: Bearer {{YOUR_API_KEY}}
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                contents:
                  type: array
                  items:
                    type: object
                    properties:
                      parts:
                        type: array
                        items:
                          type: object
                          properties:
                            text:
                              type: string
                generationConfig:
                  type: object
                  properties:
                    thinkingConfig:
                      type: object
                      properties:
                        thinkingBudget:
                          type: integer
                        includeThoughts:
                          type: boolean
                  description: 可选；thinkingConfig、thinkingBudget、includeThoughts 也均非必填。
              required:
              - contents
            example:
              contents:
              - parts:
                - text: A cat.
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties: {}
          headers: {}
          x-apifox-name: 成功
      security: []
      x-apifox-folder: 聊天(Chat)/Gemini Official Format
      x-apifox-status: released
      x-run-in-apifox: https://app.apifox.com/web/project/3868318/apis/api-350079690-run
components:
  schemas: {}
  securitySchemes: {}
servers:
- url: https://ai.t8star.org
security: []
```

**支持范围：** `gemini-3.8-flash`、`gemini-3.7-flash`。

路径为 `/v1beta/models/{model}:generateContent`，模型名放在路径中，不需要额外 body model。原固定 `/v1beta/models/gemini-2.5-pro:generateContent` 属于另一个模型路径，不能代替本项目的模型选择。

`generationConfig`、`thinkingConfig`、`thinkingBudget`、`includeThoughts` 均非必填。配置的实际思考效果未独立验证。

## Request Example

`{{MODEL}}` 选择 `gemini-3.8-flash` 或 `gemini-3.7-flash`。

Python(Requests):

```python
import requests
import json

url = "https://ai.t8star.org/v1beta/models/{{MODEL}}:generateContent"

payload = json.dumps({
   "contents": [
      {
         "parts": [
            {
               "text": "Explain how AI works in a few words"
            }
         ]
      }
   ],
   "generationConfig": {
      "thinkingConfig": {
         "thinkingBudget": 128,
         "includeThoughts": True
      }
   }
})
headers = {
   'Authorization': 'Bearer {{YOUR_API_KEY}}',
   'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
```

Python(http.client):

```python
import http.client
import json

conn = http.client.HTTPSConnection("")
payload = json.dumps({
   "contents": [
      {
         "parts": [
            {
               "text": "Explain how AI works in a few words"
            }
         ]
      }
   ],
   "generationConfig": {
      "thinkingConfig": {
         "thinkingBudget": 128,
         "includeThoughts": True
      }
   }
})
headers = {
   'Authorization': 'Bearer {{YOUR_API_KEY}}',
   'Content-Type': 'application/json'
}
conn.request("POST", "https://ai.t8star.org/v1beta/models/{{MODEL}}:generateContent", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

JavaScript:

```javascript
const myHeaders = new Headers();
myHeaders.append("Authorization", "Bearer {{YOUR_API_KEY}}");
myHeaders.append("Content-Type", "application/json");

const raw = JSON.stringify({
   "contents": [
      {
         "parts": [
            {
               "text": "Explain how AI works in a few words"
            }
         ]
      }
   ],
   "generationConfig": {
      "thinkingConfig": {
         "thinkingBudget": 128,
         "includeThoughts": true
      }
   }
});

const requestOptions = {
   method: "POST",
   headers: myHeaders,
   body: raw,
   redirect: "follow"
};

fetch("https://ai.t8star.org/v1beta/models/{{MODEL}}:generateContent", requestOptions)
   .then((response) => response.text())
   .then((result) => console.log(result))
   .catch((error) => console.error(error));
```

## Response Example

以下为 `gemini-3.1-flash-lite-image` 的真实响应，HTTP 200。Base64 与不透明 thoughtSignature 已替换为长度及 SHA-256 占位符，其他字段保留。图片位于 `candidates[].content.parts[].inlineData`，解码后为 JPEG 1408×768。证据：[实测记录 `gemini-0`](validation/2026-10-20/gemini-0.json)。

```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          {
            "inlineData": {
              "mimeType": "image/jpeg",
              "data": "[BINARY_OMITTED length=482700 sha256=b4d92041db2b525bbd320e8dd11fdb622df15e1630baa0de047c8522036336a4]"
            },
            "thoughtSignature": "[OPAQUE_VALUE_OMITTED length=658584 sha256=bb41d3506f3b967b51e5defeabb4d3762c3136a469bf02e0b14030e7a70f4e41]"
          }
        ],
        "role": "model"
      },
      "finishReason": "STOP",
      "index": 0
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 20,
    "candidatesTokenCount": 1368,
    "totalTokenCount": 1388,
    "promptTokensDetails": [
      {
        "modality": "TEXT",
        "tokenCount": 20
      }
    ],
    "candidatesTokensDetails": [
      {
        "modality": "IMAGE",
        "tokenCount": 1120
      }
    ],
    "serviceTier": "standard"
  },
  "modelVersion": "gemini-3.1-flash-lite-image",
  "responseId": "2C3XauTyJJzgytMPoJ7wkQw"
}
```

# OpenAI Chat Completions (Image analysis)

## 本项目兼容性观察（2026-10-27）

使用 `gemini-3.8-flash`、首张参考图 Data URL 和
`response_format.type=json_schema` 的一次诊断请求返回 HTTP 400。
脱敏响应明确报告：`generation_config.response_schema` 不接受 `$defs`，其嵌套属性不接受 `$ref`。
这是本供应商转发链路的观察，不是对所有 Gemini 或 OpenAI 接口的统一限制。

展开引用后的首次复测又报告嵌套 `additionalProperties` 和 `exclusiveMinimum` 不受支持。
最终适配将本地引用内联，出站移除 `additionalProperties` 并补描述，将 `exclusiveMinimum`
映射为包含边界的 minimum 加严格大于描述。完整原始 schema 放入系统提示；保留 `strict=true`
和原始 Pydantic 模型的客户端校验，未知字段、零宽高等依旧拒绝，不能将兼容子集当作完整约束。
[Google 结构化输出说明](https://ai.google.dev/gemini-api/docs/structured-output#json-schema-support)
也要求应用端验证输出；其原生接口当前支持范围不等于此供应商转发链路。
本文原始 OpenAPI 未声明 `response_format` 的支持细节；
不能仅凭 Chat Completions 兼容标识推断支持完整 JSON Schema。
本地诊断证据位于 `.cache/validation/gemini400-20261027/diagnostic-response.json`，不随交付发布。
最终首图复测中，文案和非文字画面两类分析均由 `gemini-3.8-flash` 一次请求成功，
响应经过原始 Pydantic 校验。此结论限单张参考图，不证明批量或备用模型成功路径。

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /v1/chat/completions:
    post:
      summary: Chat(分析图片)
      deprecated: false
      description: >-
        [官方指南](https://platform.openai.com/docs/guides/text-generation/chat-completions-api)

        [官方API文档](https://platform.openai.com/docs/api-reference/chat)

        所有对话模型，都可使用此接口， 修改 model 属性为模型名

        需要模型支持识图能力
      tags:
        - 聊天(Chat)
        - 模型接口/聊天接口（Chat）
      parameters:
        - name: Content-Type
          in: header
          description: ''
          required: true
          example: application/json
          schema:
            type: string
        - name: Accept
          in: header
          description: ''
          required: true
          example: application/json
          schema:
            type: string
        - name: Authorization
          in: header
          description: ''
          required: false
          example: Bearer {{YOUR_API_KEY}}
          schema:
            type: string
            default: Bearer {{YOUR_API_KEY}}
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                model:
                  type: string
                  description: >-
                    要使用的模型的 ID。有关哪些模型适用于聊天 API
                    的详细信息，请参阅[模型端点兼容性表。](https://platform.openai.com/docs/models/model-endpoint-compatibility)
                messages:
                  type: array
                  items:
                    type: object
                    properties:
                      role:
                        type: string
                      content:
                        type: string
                    x-apifox-orders:
                      - role
                      - content
                  description: >-
                    以[聊天格式](https://platform.openai.com/docs/guides/chat/introduction)生成聊天完成的消息。
                temperature:
                  type: integer
                  description: >-
                    使用什么采样温度，介于 0 和 2 之间。较高的值（如 0.8）将使输出更加随机，而较低的值（如
                    0.2）将使输出更加集中和确定。  我们通常建议改变这个或`top_p`但不是两者。
                top_p:
                  type: integer
                  description: >-
                    一种替代温度采样的方法，称为核采样，其中模型考虑具有 top_p 概率质量的标记的结果。所以 0.1 意味着只考虑构成前
                    10% 概率质量的标记。  我们通常建议改变这个或`temperature`但不是两者。
                'n':
                  type: integer
                  description: 为每个输入消息生成多少个聊天完成选项。
                stream:
                  type: boolean
                  description: >-
                    如果设置，将发送部分消息增量，就像在 ChatGPT
                    中一样。当令牌可用时，令牌将作为纯数据[服务器发送事件](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format)`data:
                    [DONE]`发送，流由消息终止。[有关示例代码](https://github.com/openai/openai-cookbook/blob/main/examples/How_to_stream_completions.ipynb)，请参阅
                    OpenAI Cookbook 。
                stop:
                  type: string
                  description: API 将停止生成更多令牌的最多 4 个序列。
                max_tokens:
                  type: integer
                  description: 聊天完成时生成的最大令牌数。  输入标记和生成标记的总长度受模型上下文长度的限制。
                presence_penalty:
                  type: number
                  description: >-
                    -2.0 和 2.0 之间的数字。正值会根据到目前为止是否出现在文本中来惩罚新标记，从而增加模型谈论新主题的可能性。 
                    [查看有关频率和存在惩罚的更多信息。](https://platform.openai.com/docs/api-reference/parameter-details)
                frequency_penalty:
                  type: number
                  description: >-
                    -2.0 和 2.0 之间的数字。正值会根据新标记在文本中的现有频率对其进行惩罚，从而降低模型逐字重复同一行的可能性。 
                    [查看有关频率和存在惩罚的更多信息。](https://platform.openai.com/docs/api-reference/parameter-details)
                logit_bias:
                  type: 'null'
                  description: >-
                    修改指定标记出现在完成中的可能性。  接受一个 json 对象，该对象将标记（由标记器中的标记 ID 指定）映射到从
                    -100 到 100 的关联偏差值。从数学上讲，偏差会在采样之前添加到模型生成的 logits
                    中。确切的效果因模型而异，但 -1 和 1 之间的值应该会减少或增加选择的可能性；像 -100 或 100
                    这样的值应该导致相关令牌的禁止或独占选择。
                user:
                  type: string
                  description: >-
                    代表您的最终用户的唯一标识符，可以帮助 OpenAI
                    监控和检测滥用行为。[了解更多](https://platform.openai.com/docs/guides/safety-best-practices/end-user-ids)。
              required:
                - model
                - messages
              x-apifox-orders:
                - model
                - messages
                - temperature
                - top_p
                - 'n'
                - stream
                - stop
                - max_tokens
                - presence_penalty
                - frequency_penalty
                - logit_bias
                - user
            example:
              model: gpt-4o
              stream: false
              messages:
                - role: user
                  content:
                    - type: text
                      text: 这张图片有什么
                    - type: image_url
                      image_url:
                        url: >-
                          https://github.com/dianping/cat/raw/master/cat-home/src/main/webapp/images/logo/cat_logo03.png
              max_tokens: 81920
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: string
                  object:
                    type: string
                  created:
                    type: integer
                  choices:
                    type: array
                    items:
                      type: object
                      properties:
                        index:
                          type: integer
                        message:
                          type: object
                          properties:
                            role:
                              type: string
                            content:
                              type: string
                          required:
                            - role
                            - content
                          x-apifox-orders:
                            - role
                            - content
                        finish_reason:
                          type: string
                      x-apifox-orders:
                        - index
                        - message
                        - finish_reason
                  usage:
                    type: object
                    properties:
                      prompt_tokens:
                        type: integer
                      completion_tokens:
                        type: integer
                      total_tokens:
                        type: integer
                    required:
                      - prompt_tokens
                      - completion_tokens
                      - total_tokens
                    x-apifox-orders:
                      - prompt_tokens
                      - completion_tokens
                      - total_tokens
                required:
                  - id
                  - object
                  - created
                  - choices
                  - usage
                x-apifox-orders:
                  - id
                  - object
                  - created
                  - choices
                  - usage
          headers: {}
          x-apifox-name: OK
      security: []
      x-apifox-folder: 聊天(Chat)
      x-apifox-status: released
      x-run-in-apifox: https://app.apifox.com/web/project/3868318/apis/api-139453850-run
components:
  schemas: {}
  securitySchemes: {}
servers: []
security: []

```

## Request Example

`{{MODEL}}` 选择 `gemini-3.8-flash` 或 `gemini-3.7-flash`。

Python(Requests):

```python
import requests
import json

url = "https://ai.t8star.org/v1/chat/completions"

payload = json.dumps({
   "model": "{{MODEL}}",
   "stream": False,
   "messages": [
      {
         "role": "user",
         "content": [
            {
               "type": "text",
               "text": "这张图片有什么"
            },
            {
               "type": "image_url",
               "image_url": {
                  "url": "https://github.com/dianping/cat/raw/master/cat-home/src/main/webapp/images/logo/cat_logo03.png"
               }
            }
         ]
      }
   ],
   "max_tokens": 81920
})
headers = {
   'Accept': 'application/json',
   'Authorization': 'Bearer {{YOUR_API_KEY}}',
   'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
```

Python(http.client):

```python
import http.client
import json

conn = http.client.HTTPSConnection("")
payload = json.dumps({
   "model": "{{MODEL}}",
   "stream": False,
   "messages": [
      {
         "role": "user",
         "content": [
            {
               "type": "text",
               "text": "这张图片有什么"
            },
            {
               "type": "image_url",
               "image_url": {
                  "url": "https://github.com/dianping/cat/raw/master/cat-home/src/main/webapp/images/logo/cat_logo03.png"
               }
            }
         ]
      }
   ],
   "max_tokens": 81920
})
headers = {
   'Accept': 'application/json',
   'Authorization': 'Bearer {{YOUR_API_KEY}}',
   'Content-Type': 'application/json'
}
conn.request("POST", "https://ai.t8star.org/v1/chat/completions", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

JavaScript:

```javascript
const myHeaders = new Headers();
myHeaders.append("Accept", "application/json");
myHeaders.append("Authorization", "Bearer {{YOUR_API_KEY}}");
myHeaders.append("Content-Type", "application/json");

const raw = JSON.stringify({
   "model": "{{MODEL}}",
   "stream": false,
   "messages": [
      {
         "role": "user",
         "content": [
            {
               "type": "text",
               "text": "这张图片有什么"
            },
            {
               "type": "image_url",
               "image_url": {
                  "url": "https://github.com/dianping/cat/raw/master/cat-home/src/main/webapp/images/logo/cat_logo03.png"
               }
            }
         ]
      }
   ],
   "max_tokens": 81920
});

const requestOptions = {
   method: "POST",
   headers: myHeaders,
   body: raw,
   redirect: "follow"
};

fetch("https://ai.t8star.org/v1/chat/completions", requestOptions)
   .then((response) => response.text())
   .then((result) => console.log(result))
   .catch((error) => console.error(error));
```

## Response Example

```json
{
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "created": 1677652288,
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "\n\nHello there, how may I assist you today?"
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 9,
        "completion_tokens": 12,
        "total_tokens": 21
    }
}
```
