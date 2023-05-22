const { Configuration, OpenAIApi } = require("openai");
const configuration = new Configuration({
    apiKey: "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",
});
const openai = new OpenAIApi(configuration);
async function ask(prompt) {
    const response = await openai.createCompletion({
        model: "gpt-3.5-turbo",
        prompt,
        temperature: 0.7,
        max_tokens: 256,
        top_p: 1,
        frequency_penalty: 0,
        presence_penalty: 0,
    });
const answer = response.data.choices[0].text;
console.log(answer);
}
//Ask an example question
ask("oi?");