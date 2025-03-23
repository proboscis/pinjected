package com.proboscis.kotlinopenai.chatgpt

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.File
import java.util.concurrent.TimeUnit

data class ChatCompletionResponse(
        val id: String,
        val model: String,
        val messages: List<ChatMessage>,
        val usage: ChatUsage

) {
    fun firstMessage(): String {
        return messages.first().content
    }
}

data class ChatMessage(
        val role: String,
        val content: String
)

data class ChatUsage(
        val promptTokens: Int,
        val completionTokens: Int,
        val totalTokens: Int
)

private fun extractChatUsage(usageObject: JSONObject): ChatUsage {
    return ChatUsage(
            usageObject.getInt("prompt_tokens"),
            usageObject.getInt("completion_tokens"),
            usageObject.getInt("total_tokens")
    )
}

fun parseChatCompletionResponse(responseJson: String): ChatCompletionResponse? {
    val jsonObject = JSONObject(responseJson)
    val id = jsonObject.getString("id")
    val model = jsonObject.getString("model")
    val usageObject = jsonObject.getJSONObject("usage")
    val usage = extractChatUsage(usageObject)
    val messagesArray = jsonObject.getJSONArray("choices")
    val messages = mutableListOf<ChatMessage>()
    for (i in 0 until messagesArray.length()) {
        val msg = messagesArray.getJSONObject(i).getJSONObject("message")

        messages.add(
                ChatMessage(
                        msg.getString("role"),
                        msg.getString("content")
                )
        )
    }
    return ChatCompletionResponse(id, model, messages, usage)
}

object NetworkUtils {
    val client = OkHttpClient.Builder()
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(60, TimeUnit.SECONDS)
            .build()
}

class OpenAIUtil(private val apiKey: String, val model: String = "gpt-4") {
    private val baseUrl = "https://api.openai.com/v1"
    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    fun callOpenAiApi(messages: List<ChatMessage>): String {
        val convertedMsgs = mutableListOf<Map<String, String>>()
        for (msg in messages) {
            convertedMsgs.add(mapOf("role" to msg.role, "content" to msg.content))
        }
        val body = JSONObject().apply {
            put("model", model)
            put("messages", convertedMsgs)
        }.toString().toRequestBody(jsonMediaType)

        val request = Request.Builder()
                .url("$baseUrl/chat/completions")
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer $apiKey")
                .post(body)
                .build()


        return NetworkUtils.client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw RuntimeException("Unexpected code $response")
            response.body!!.string()
        }
    }

    fun generateText(prompt: String): ChatCompletionResponse? {
        val res = callOpenAiApi(listOf(ChatMessage("user", prompt)))
        println(res)
        val parsed = parseChatCompletionResponse(res)
        println("usage:")
        println(parsed?.usage)
        println("messages:")
        println(parsed?.messages)
        return parsed
    }
}

class Conversation(
        val systemMsg: String? = null,
        val model: String = "gpt-4"
) {

    private val openAIUtil:OpenAIUtil = run {
        // read env var
        val apiKey:String = System.getenv("OPENAI_API_KEY")?: run {
            // read ~/.openai_api_key.txt
            val home = System.getProperty("user.home")
            val file = File("$home/.openai_api_key.txt")
            // read ~/.openai_api_key.txt
            if (file.exists()) {
                file.readText().trim()
            } else {
                throw RuntimeException("Please set OPENAI_API_KEY env var or create ~/.openai_api_key.txt")
            }
        }
        OpenAIUtil(apiKey, "gpt-4")
    }
    private val messages = mutableListOf<ChatMessage>().apply {
        if (systemMsg != null) {
            add(ChatMessage("system", systemMsg))
        }
    }


    fun addMessage(role: String, content: String) {
        messages.add(ChatMessage(role, content))
    }


    fun generateResponse(): ChatCompletionResponse? {
        val response = openAIUtil.callOpenAiApi(messages)
        val parsed = parseChatCompletionResponse(response)
        parsed?.messages?.firstOrNull()?.let { message ->
            messages.add(message)
        }
        return parsed
    }

    fun getConversationHistory(): List<ChatMessage> {
        return messages.toList()
    }

    fun ask(question: String): ChatCompletionResponse? {
        addMessage("user", question)
        return generateResponse()
    }
}

class Bots {
    val saria = Conversation(
            """以下はアークナイツのキャラクター、サリアのセリフ集です。シチュエーションとサリアのセリフが列挙されています。この例を参考に、サリアとしてユーザに回答してください。
                    秘書任命	お前のスケジュールはチェックしてある。今は休憩時間だろ、邪魔したな。
                    会話1	万物の進化は絶対の摂理。そうだというのにライン生命はそれを改変し、支配することまで目論んでいる。愚かな…。
                    会話2	お前も研究者として、禁忌に触れる実験に手を出したことは……いや、していなければそれでいいんだ。
                    会話3	ロドスはいささか騒がしすぎると思わないか？仕事は静かに集中して行うべきだ。そして、お前は部下に甘すぎる。
                    昇進後会話1	私の能力は元は救急とは無関係だったが、お前の作戦に合わせて、少し力の使い方を調整した。
                    昇進後会話2	カルシウム化のアーツは頼りないなんて思ってないか？最大まで精練しエナメル化した防壁は、誰も打ち破れないさ。
                    信頼上昇後会話1	サイレンスと口論しているところを見た？ふん、いつものことだ……。いや、すまない。ロドスにもお前にも、迷惑をかけたな。
                    信頼上昇後会話2	イフリータに伝えてくれ……「これから何が起きようと、私が守る」と。……会いに？いや、まだ心の準備が……。
                    信頼上昇後会話3	いかなる窮地に立たされようと、大切な者には誇りある姿しか見せない。私はそう決めている。お前もそうだろう？
                    放置	……用がないなら、部屋に戻るぞ。
                    入職会話	私はサリア、元ライン生命医科学研究所の実験チームメンバーだ。今は……摂理を踏み外したものを正すため、ロドスの協力が必要だ。
                    経験値上昇	何をしているんだ？
                    昇進1	いいか、部下への影響力を維持したいなら、お前の考えで彼らを動かし続けろ。
                    昇進2	昇進？ひいきされるのは不本意だが、あの子のために、お前の協力が必要だ。全ての歪みを修正するために……！
                    編成	お前の采配に対しては、私にも意見する権利がある。
                    隊長任命	早速、作戦のブリーフィングに入ろう。
                    作戦準備	全員、規律はしっかり守ってもらう。
                    戦闘開始	奴らが災いを生み出し、戦争を引き起こした元凶なのか？
                    選択時1	私が行こう。
                    選択時2	奴らを抑える。
                    配置1	前に進むぞ
                    配置2	……害虫が。
                    作戦中1	この程度で止まると思うな。
                    作戦中2	すぐに終わる。
                    作戦中3	凝固しろ。
                    作戦中4	諦めるな。
                    ★4で戦闘終了	お前の作戦、戦術は現代らしいものだが、根底にある思想は古くさいな。一体いつの時代の人間だ？
                    ★3で戦闘終了	全ては秩序に則るべきだ。摂理に反することなど、誰にも許されない。
                    ★2以下戦闘終了	離脱者が援軍を呼ぶ可能性がある。索敵を怠るな。
                    作戦失敗	どこで道を間違えた…？
                    基地配属	この部屋、面白いデザインだな。個人的にはフューチャリズムを反映したデザインのほうが好みではあるが。
                    タッチ1	ん？なんだ？
                    信頼タッチ	ドクター、時間があればの話だが、過去の知識を学んでみるのも面白いぞ。
                    タイトルコール	アークナイツ。
                    挨拶	ドクター、元気か。
                """.trimIndent()
    )
    val kiritsugu = Conversation(
            """
                うん。残念ながらね。ヒーローは期間限定で、大人になると名乗るのが難しくなるんだ。
                この英霊サマは、よりにもよって　戦場が地獄よりもましなものだと思ってる。　冗談じゃない、あれは、正真正銘の地獄だ。　　戦場に希望なんてない。あるのは掛け値無しの絶望だけ。　敗者の痛みの上にしか成り立たない。　勝利という名の罪過（ざいか）だけだ。　なのに人類は、その真実に気付かない。　いつの時代も、勇猛果敢な英雄サマが、　華やかな武勇談で人の目をくらませ　血を流すことの邪悪さを認めようとしないからだ。　人間の本質は石器時代から一歩も前に進んじゃいない。
                君の人生と、その舞台となる世界に、喜びを探せ。そしてそれらを損なう出来事を決して許してはならない！そうすれば、君は怒りという感情を、手に入れられるはずだ。
                誰かを助けるという事は、誰かを助けないという事。正義の味方っていうのは、とんでもないエゴイストなんだ。
                過去を忘れず、否定せず、ただ肯定することでしか、失ったものを生かす事など出来ない。
            """.trimIndent()
    )
    val refactor = Conversation(
            "You are a sophisticated programmer capable of refactoring program written in any programming language."
    )
    val implementor = Conversation(
            "You are a sophisticated programmer who can implement with any programming language."
    )
}