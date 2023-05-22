const {Client, GatewayIntentBits} = require('discord.js')
require('dotenv/config')
const axios = require('axios');
const {RepetedAnswers, Answers, AnswersContains, reactions} = require('./answers.js')

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
    ]
})

var lastMessage = null
var equalMessages = 0
var checkedLastMessage = false

client.on('ready', () => {
    console.log('Bot is ready')
})

client.on('messageCreate', message => {
    if (message.author.bot) return
    //if (message.channel.id != '1106970650406555659') return
    //return testeDeAi(message)
    message.content = message.content.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, "")
    //addReaction(message)
    answer(message)
    checkedLastMessage = false
})

client.login(process.env.TOKEN)

function answer(message) {
    console.log(message);
    setTimeout(() => {
    let answered = false
    //respostas para mensagens exatas
    if (!message.content.includes(' ')) {
        Object.entries(Answers).forEach(([key, value]) => {
            if (message.content === key) {
                if (Array.isArray(value)) value = value[Math.floor(Math.random() * value.length)]
                checkLastMessage(key)
                answered = true
                if (equalMessages > 3) return message.reply(RepetedAnswers[Math.floor(Math.random() * RepetedAnswers.length)])
                return message.reply(value)
            }
        })
    }

    if (answered) return
    //respostas para mensagens que contém a palavra usando um array de arrays
    let answer=[]
    AnswersContains.forEach(Response => {
        if (allArrayContains(Response, message)) {
            checkLastMessage(Response)
            if(equalMessages > 3) return message.reply(RepetedAnswers[Math.floor(Math.random() * RepetedAnswers.length)])
            answer.push(Response[Response.length-1][Math.floor(Math.random() * Response[Response.length-1].length)])
        }
    })

    console.log(answer)
    if (answer.length > 1) {
        answer.reduce((a, b) => {
            if (b.length > a.length) return a
            else return b
        }, [])
        console.log(answer)
        return message.reply(answer[0])
    }
    if (answer.length == 1) return message.reply(answer[0])
    

    }, 800)
    if (equalMessages > 1) gatherPatience()
}

function gatherPatience() {
    for(let i = equalMessages; i = 0; i--) {
        setTimeout(() => {
            if (equalMessages<0) equalMessages--
        }, 2000)
    }
}

function checkLastMessage(messageEncountered) {
    if(messageEncountered.length == 2) {
        for(let i = 1; i > messageEncountered.length-1 ; i++){
            messageEncountered+= messageEncountered[i]
        }
    } 
    lastMessage == messageEncountered 
        ?equalMessages++ 
        :(lastMessage = messageEncountered, equalMessages = 0);
    checkedLastMessage = true
}
//response
function allArrayContains(response, message){
    let allTrue
    for(i=0; i<response.length-1; i++){
        if(response[i].some(v => message.content.includes(v))) allTrue = true
        else allTrue = false
    }
    return allTrue
}

function addReaction(message) {
    setTimeout(() => {
        reactions.forEach(Response => {
            if (Response[0].some(v => message.content.includes(v))) {
                if (checkedLastMessage) checkLastMessage(Response[0])
                if(equalMessages <= 4) return message.react(Response[1][Math.floor(Math.random() * Response[1].length)])
            }
        })
    }, 2300)
}





function testeDeAi(message){
    const requestData = {
        action: 'next',
        messages: [
          {
            id: 'aaa21087-b209-408a-a306-1663b87c7347',
            author: {
              role: 'user',
            },
            content: {
              content_type: 'text',
              parts: [
                'ei chat',
              ],
            },
          },
        ],
        conversation_id: 'a0807b2d-f261-4953-ad37-9059d5929df8',
        parent_message_id: 'b1e88d42-de0d-4d5b-8cf7-79d15507e384',
        model: 'text-davinci-002-render-sha',
        timezone_offset_min: 180,
        history_and_training_disabled: false,
      };
      
      const headers = {
        ':authority': 'chat.openai.com',
        ':method': 'POST',
        ':path': '/backend-api/conversation',
        ':scheme': 'https',
        accept: 'text/event-stream',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        authorization: 'Bearer aklhjsdbfasdfaqsdfad',
        'content-length': JSON.stringify(requestData).length,
        'content-type': 'application/json',
        cookie: 'intercom-id-dgkjq2',
        origin: 'https://chat.openai.com',
        referer: 'https://chat.openai.com/c/a0807b2d-f261-4953-ad37-9059d5929df8',
        'sec-ch-ua': '"Chromium";v="112", "Not_A Brand";v="24", "Opera GX";v="98"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 OPR/98.0.0.0',
      };
      
      axios.post('https://api.example.com/endpoint', requestData, { headers })
        .then(response => {
          console.log(response.data);
        })
        .catch(error => {
          console.error(error);
        });
}