

const RepetedAnswers = [
    'ok, acho que da pra você parar de repetir isso agora né? u.u',
    'você pode parar de repetir isso, por favor?',
    'ta, acho que ja da pra parar né?',
    'ok, mas agora chega né?',
    'ta fazendo isso de propósito né?',
    'você não cansa não?',
    'você não tem mais nada pra fazer não?',
    'ta bom, eu desisto',
    'ok, você venceu',
    'ok, você ganhou',
    'ok, você conseguiu',
    'ok, você me venceu',
    'meep, ja deu',
    'meep, chega',
    'pareee',
    'paraaaa',
    'chegaaaaa',
    'para por favor',
    'para com isso',
    'para pelo amor de deus',
    'para, por favor',
    'para, por favorzinho',
    'por favor, para, eu nunca te pedi nada',
    'para, eu imploro',
    'vamo parar?',
]

const Answers = {
    'ping': 'pong',
    'boop': 'boop boop',
    'tik': 'tok',
    'coddy': [
        'oi?',
        'oi! :3',
        'olá! :3',
        'euzinho! :3',
        'me chamou?',
        'fui chamado? :3',
        'tô aqui, pode falar',
        'oi, em que posso ajudar? :3',
        'oiiie <:catsip:851024825333186560>'
    ],
    'coddy?': [
        'oi?',
        'oi! :3',
        'olá! :3',
        'me chamou?',
        'oi! to aqui',
        'euzinho! :3',
        'fui chamado? :3',
        'tô aqui, pode falar',
        'oi, em que posso ajudar? :3',
        'oiiie <:catsip:851024825333186560>'
    ],
    'roi': [
        'roi roi',
        'roie ;3',
        'roi, leticia né?',
        'roi <:catsip:851024825333186560>',
    ],
};    

const AnswersContains = [
    [
        [
            'nosso novo mascote',
            'mascote da brafurries'
        ],
        [
            'falou de mim? uwu', 
            'euzinho aqui :3', 
            'me chamou? uwu',
            'Estou à disposição! :3',
            'O que posso fazer por você? :3',
            'Pronto para animar o ambiente!',
            'Estou aqui para ajudar! :3',
            'pronto para servir! :3',
            'Estou aqui para o que precisar! :3',
        ]
    ],
    [
        [
            'bom dia coddy',
            'bomdia coddy',
            'bodia coddy',
        ],
        [
            'bom dia! :3',
            'boooom dia! :3', 
            'buenos dias uwu', 
            'que o sol ja nasceu lá na fazendinha!', 
            'bom dia, como vai? :3'
        ],
    ],
    [
        [
            'boa tarde coddy',
            'buenas tardes coddy',
            'batarde coddy'
        ],
        [
            'boa tarde! :3',
            'buenas tardes uwu',
            'boa tarde, como vai? :3',
        ],
    ],
    [
        [
            'boa noite coddy',
            'bonotche coddy',
        ],
        [
            'boa noite! :3',
            'buenas noches uwu',
            'boa noite, como vai? :3',
            'tenha bons sonhos! :3',
            'tenha uma boa noite! :3',
            'ja vai dormir? ',
        ],
    ],
    [
        [
            'oi coddy',
            'ola coddy',
        ],
        [
            'oi! :3',
            'olá! :3',
            'hellouzinho! :3',
            'oizinho! uwu',
            'oizinho! ;3',
            'falou de mim?',
            'ficou com saudades? :3',
            'fui chamado? :3',
            'oi, em que posso ajudar? :3',
            'fui buscar pão, me chama daqui a pouco',
        ],
    ],
    /* [
        [
            'coddy'
        ],
        [
            'tudo bem'
        ],
        [
            '?'
        ],
        [
            'tudo sim e contigo? :3',
            'tudo ótimo e contigo? :3',
            'tudo bão e contigo? :3',
            'tudo bom e você? :3',
            'tudo ótimo e você? :3',
            'tudo maravilhosamente bem e você? :3',
            'tudo maravilhosamente bem e contigo? :3',
            'melhor agora que você chegou! uwu',
        ]
    ], */
    [
        [
            'tchau coddy',
        ],
        [
            'tchau! :3',
            'até mais! :3',
            'até logo! :3',
            'ja vai?',
        ]
    ],
    [
        [
            'obrigado coddy',
        ],
        [
            'de nada! :3',
            'por nada! :3',
            'não foi nada! :3',
            'não precisa agradecer! :3',
            'não foi nada demais! :3',
            'disponha! :3',
            'estou aqui para ajudar! :3',
            'estou aqui para o que precisar! :3',
            'de nada uwu',
            'por nada uwu',
            'qualquer coisa é só chamar! ;3',
        ]
    ],
    [
        [
            'coddy'
        ],
        [
            'boboca'
        ],
        [
            'sou nada'
        ]
    ],
    [
        [
            'coddy',
        ],
        [
            'falar com',
            'pedir ajuda do',
            'pedir ajuda para o',
        ],
        [
            'precisando de mim?',
            'em que posso ajudar?',
            'ajudo em alguma coisa?',
            'o que posso fazer por você?',
        ]
    ],/////////////////////////////////////////////////////////////
    [
        [
            'coddy',
        ],
        [
            'ne?',
            'ne'
        ],
        [
            'né! :3',
            'né né? :3',
            'se voce ta dizendo uwu',
            'concordo uwu',
            'pode ser, porém depende',
            'depende, mas pode ser',
            'concordo, mas tambem discordo',
            'discordo, mas tambem concordo',
            'será mesmo?',
            'pode ser que sim, pode ser que não',
            'talvez',
            'depende do ponto de vista',
            'olha, eu não sei',
            'não sei, mas acho que não',
        ]
    ],
    [
        [
            'coddy',
        ],
        [
            'voce pode fazer?',
            'voce faz?',
            'voce sabe fazer?',
        ],
        [
            'olha, eu sei fazer algumas coisas, tipo responder algumas perguntas',
            'eu sei fazer algumas coisas que me programaram pra fazer, tipo responder algumas perguntas, mas só aquelas que me ensinaram',
            'atualmente, não sei fazer muita coisa, mas estou aprendendo',
            'só sei fazer o que me ensinaram, mas estou aprendendo mais coisas',
        ]
    ],
    [
        [
            'coddy',
        ],
        [
            'chato',
            'irritante',
            'esquisito',
            'estranho',
        ],
        [
            'não fala assim de mim, eu sou sensivel... :c',
            'porquêeee? :c',
            'o que eu fiz? :c',
            'eu não sou assim :c',
        ]
    ],///////////////////////////////////////////////////////////////
    [
        [
            'coddy',
            'nosso mascote',
        ],
        [
            'lindo',
            'lindinho',
            'fofo',
            'bonito',
            'gato',
            'gatinho',
            'cheiroso',
            'fofinho',
            'fofucho',
            'fofuxo',
            'fofin',
            'charmoso',
            'adoravel',
            'amavel',
            'amoroso',
            'apertavel',
            'gracinha',
            'princeso',
            'principe',
        ],
        [
            'obrigado! :3',
            'obrigadinho uwu',
            'awwwwn, obrigado! :3',
            'nhaiiii, obrigado x3',
            'nananinanão, você uwu',
            'eu não sou tudo isso vai uwu',
            'alá, ta querendo alguma coisa',
            'me ilude menos uwu brincadeira, obrigado! :3',
            'obrigado, você também é um amor! :3',
            'para, eu fico sem graça assim uwu',
            'para, eu fico sem graça assim x3',
            'para, você que é uwu',
            'eu tambem acho uwu',
            'eu tambem acho :3',
            'me elogia naum, por obséquio uwu',
            'para de me elogiar x3',
        ]
    ],
]

const reactions = [
    [
        [
            'coddy',
        ],
        [
            '<:firlove:964945806522220634>',
            '<:catsip:851024825333186560>',
            '<:altruisticpat:964945806408962099>',
            '<a:bongo_cat:851028093472735232>',
            '<:happydoggo:791023648432455722>'
        ]
    ],
]

module.exports = { RepetedAnswers, Answers, AnswersContains, reactions };