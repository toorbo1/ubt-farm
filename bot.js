const TelegramBot = require('node-telegram-bot-api');
require('dotenv').config();

const bot = new TelegramBot(process.env.BOT_TOKEN, { polling: true });

// Хранилище данных пользователей (в реальном проекте используйте БД)
const userData = {};

// Отслеживаем сообщения бота для удаления
const botMessages = {}; // { chatId: [messageId1, messageId2, ...] }

// Функция для сохранения ID сообщений бота
async function saveBotMessageId(chatId, messageId) {
  if (!botMessages[chatId]) {
    botMessages[chatId] = [];
  }
  botMessages[chatId].push(messageId);
}

// Функция для удаления всех сообщений бота в чате
async function deleteAllBotMessages(chatId) {
  const messages = botMessages[chatId] || [];
  for (const msgId of messages) {
    try {
      await bot.deleteMessage(chatId, msgId);
    } catch (e) {
      // Игнорируем ошибки (сообщение уже удалено или не найдено)
    }
  }
  botMessages[chatId] = [];
}

// Inline-клавиатуры
const mainMenu = {
  reply_markup: {
    inline_keyboard: [
      [{ text: '🧪 Тест-драйв VPN', callback_data: 'test_drive' }],
      [{ text: '💎 Подписка', callback_data: 'subscription' }, { text: '🎁 Есть код?', callback_data: 'promo' }],
      [{ text: '💸 Зови друзей', callback_data: 'referral' }],
      [{ text: '🆘 Каролина, помоги', callback_data: 'help' }, { text: '✨ О Ventura', callback_data: 'about' }]
    ]
  }
};

// Клавиатура для раздела "Мой доступ"
const accessMenu = {
  reply_markup: {
    inline_keyboard: [
      [{ text: '⚡ Продлить доступ', callback_data: 'renew' }, { text: '🔐 Забрать ключ', callback_data: 'key' }],
      [{ text: '📲 Мои устройства', callback_data: 'devices' }, { text: '🌎 Куда летим?', callback_data: 'servers' }],
      [{ text: '♻️ Связать аккаунты', callback_data: 'link_accounts' }],
      [{ text: '🏠 К Каролине', callback_data: 'home' }]
    ]
  }
};

// Помощь
const helpMenu = {
  reply_markup: {
    inline_keyboard: [
      [{ text: '🔑 Не работает ключ', callback_data: 'help_key' }],
      [{ text: '🌍 Не подключается сервер', callback_data: 'help_server' }],
      [{ text: '💳 Вопрос по оплате', callback_data: 'help_payment' }],
      [{ text: '💬 Связаться с человеком', callback_data: 'human_support' }],
      [{ text: '🏠 К Каролине', callback_data: 'home' }]
    ]
  }
};

// Меню тест-драйва
const testDriveMenu = {
  reply_markup: {
    inline_keyboard: [
      [{ text: '🔐 Вставить ключ', callback_data: 'insert_key' }],
      [{ text: '🌎 Выбрать сервер', callback_data: 'servers' }],
      [{ text: '🏠 К Каролине', callback_data: 'home' }]
    ]
  }
};

// Меню подписки
const subscriptionMenu = {
  reply_markup: {
    inline_keyboard: [
      [{ text: '📅 На месяц', callback_data: 'sub_1m' }],
      [{ text: '🔥 На 6 месяцев', callback_data: 'sub_6m' }],
      [{ text: '💎 На год', callback_data: 'sub_12m' }],
      [{ text: '🏠 К Каролине', callback_data: 'home' }]
    ]
  }
};

// Функция для удаления всех старых сообщений бота (кроме текущего) и отправки нового
async function replaceMessage(chatId, messageId, text, options = {}) {
  // Удаляем все предыдущие сообщения бота КРОМЕ текущего (на которое нажал пользователь)
  const messages = botMessages[chatId] || [];
  for (const msgId of messages) {
    if (msgId !== messageId) { // Не удаляем текущее сообщение
      try {
        await bot.deleteMessage(chatId, msgId);
      } catch (e) {
        // Игнорируем ошибки
      }
    }
  }
  botMessages[chatId] = [messageId]; // Сохраняем только текущее

  // Отправляем новое сообщение и сохраняем его ID
  const msg = await bot.sendMessage(chatId, text, options);
  saveBotMessageId(chatId, msg.message_id);
  return msg;
}

// Функция для отправки приветственных сообщений (стикер + текст + кнопки)
async function sendWelcomeMessages(chatId, messageId, text1, text2, stickerEmoji, options2 = {}) {
  // Удаляем ВСЕ предыдущие сообщения бота в этом чате (кроме /start пользователя)
  await deleteAllBotMessages(chatId);

  // Отправляем стикер если есть ID и сохраняем ID
  const stickerId = process.env.WELCOME_STICKER_ID;
  if (stickerId && stickerId.length > 0) {
    try {
      const stickerMsg = await bot.sendSticker(chatId, stickerId);
      saveBotMessageId(chatId, stickerMsg.message_id);
    } catch (e) {
      console.log('Ошибка отправки стикера:', e.message);
    }
  }
  // Затем текст и сохраняем ID
  const textMsg = await bot.sendMessage(chatId, text1);
  saveBotMessageId(chatId, textMsg.message_id);
  // И кнопки (если есть) и сохраняем ID
  if (text2 && text2.length > 0) {
    const buttonsMsg = await bot.sendMessage(chatId, text2, options2);
    saveBotMessageId(chatId, buttonsMsg.message_id);
    return buttonsMsg;
  }
}

// Функция для удаления всех сообщений бота в чате
async function deleteAllBotMessages(chatId) {
  // Получаем информацию о чате (количество сообщений)
  try {
    const chat = await bot.getChat(chatId);
    // Telegram не даёт получить список сообщений, поэтому удаляем последние N
    for (let i = 0; i < 20; i++) {
      try {
        await bot.deleteMessage(chatId, chat.last_message_id - i);
      } catch (e) {
        break; // Нет больше сообщений для удаления
      }
    }
  } catch (e) {
    // Игнорируем ошибки
  }
}

// Функция для показа временного сообщения загрузки
async function showLoadingMessage(chatId, messageId) {
  const loadingMsg = await bot.sendMessage(chatId, 'ту-ту-туууу... ⏳');
  saveBotMessageId(chatId, loadingMsg.message_id);
  return loadingMsg.message_id;
}

// Функция для скрытия временного сообщения загрузки
async function hideLoadingMessage(chatId, messageId) {
  try {
    await bot.deleteMessage(chatId, messageId);
  } catch (e) {
    // Игнорируем ошибку
  }
}

// Стикеры из пака VenturaVpn (используем стандартный emoji стикер)
const STICKERS = {
  WELCOME: '🚀', // используем emoji как fallback
};

// Приветственное сообщение (3 отдельных сообщения: стикер + текст + кнопки)
bot.onText(/^\/start$/, async (msg) => {
  const chatId = msg.chat.id;
  const messageId = msg.message_id;
  const welcomeMessage = `Привет!`;

  // Удаляем старые сообщения бота
  await deleteAllBotMessages(chatId);

  // 1. Отправляем стикер если есть ID
  const stickerId = process.env.WELCOME_STICKER_ID;
  if (stickerId && stickerId.length > 0) {
    try {
      const stickerMsg = await bot.sendSticker(chatId, stickerId);
      saveBotMessageId(chatId, stickerMsg.message_id);
    } catch (e) {
      console.log('Ошибка отправки стикера:', e.message);
    }
  }

  // 2. Отправляем текст
  const textMsg = await bot.sendMessage(chatId, welcomeMessage);
  saveBotMessageId(chatId, textMsg.message_id);

  // 3. Отправляем кнопки
  const buttonsMsg = await bot.sendMessage(chatId, 'Выбирай, что интересно:', mainMenu);
  saveBotMessageId(chatId, buttonsMsg.message_id);
});

// Обработка всех callback_query
bot.on('callback_query', async (query) => {
  const chatId = query.message.chat.id;
  const messageId = query.message.message_id;
  const data = query.data;

  await bot.answerCallbackQuery(query.id);

  // Показываем временное сообщение загрузки
  let loadingMsgId = null;
  const showLoading = async () => {
    loadingMsgId = await showLoadingMessage(chatId, messageId);
  };

  // Скрываем временное сообщение загрузки
  const hideLoading = async () => {
    if (loadingMsgId) {
      await hideLoadingMessage(chatId, loadingMsgId);
    }
  };

  // Имитация загрузки для демонстрации
  const simulateLoading = async (delay, callback) => {
    await showLoading();
    setTimeout(async () => {
      await hideLoading();
      await callback();
    }, delay);
  };

  switch (data) {
    case 'test_drive': {
      await simulateLoading(1500, async () => {
        const message = `🧪 Тест-драйв VPN

Попробуй VenturaVPN бесплатно! Вставь ключ и наслаждайся свободным интернетом 🎉`;
        await replaceMessage(chatId, messageId, message, testDriveMenu);
      });
      break;
    }

    case 'subscription': {
      await simulateLoading(1000, async () => {
        const message = `💎 Выбери подписку

Чем дольше подписка — тем больше выгода! 🔥`;
        await replaceMessage(chatId, messageId, message, subscriptionMenu);
      });
      break;
    }

    case 'insert_key': {
      await simulateLoading(800, async () => {
        const message = `🔐 Вставь свой ключ доступа

Отправь мне ключ сообщением, и я помогу его активировать ✨`;
        await replaceMessage(chatId, messageId, message);

        // Создаём уникальный хендлер для этого чата
        const handlerKey = `insert_key_${chatId}`;

        const handler = async (keyMsg) => {
          if (keyMsg.chat.id === chatId && !keyMsg.text?.startsWith('/')) {
            const successMessage = `✅ Ключ принят!

Теперь ты можешь пользоваться VenturaVPN на полной скорости 🚀`;
            // Удаляем только этот хендлер
            bot.off('message', handler);
            await replaceMessage(chatId, keyMsg.message_id, successMessage, mainMenu);
          }
        };
        bot.on('message', handler);
      });
      break;
    }

    case 'promo': {
      await simulateLoading(800, async () => {
        const message = `🎁 Есть секретный код?

Отправь его мне сообщением и я проверю бонусы ✨`;
        await replaceMessage(chatId, messageId, message);

        // Ожидаем промокод
        const handler = async (promoMsg) => {
          if (promoMsg.chat.id === chatId && !promoMsg.text?.startsWith('/')) {
            const successMessage = `🔥 Отлично!

Промокод успешно применён.`;
            bot.off('message', handler);
            await replaceMessage(chatId, promoMsg.message_id, successMessage, mainMenu);
          }
        };
        bot.on('message', handler);
      });
      break;
    }

    case 'referral': {
      await simulateLoading(1200, async () => {
        const userId = query.from.id;
        const referralLink = `https://t.me/VenturaVPNBot?start=ref${userId}`;
        const message = `💸 Зарабатывай вместе с VenturaVPN

Приглашай друзей и получай бонусы за их покупки 🚀

👥 Друзей: 0

💰 Баланс: 0 ₽

🏆 Доход:
15% с первой покупки
10% с продлений

🔗 Твоя ссылка:
${referralLink}`;

        await replaceMessage(chatId, messageId, message, mainMenu);
      });
      break;
    }

    case 'help': {
      await simulateLoading(1000, async () => {
        const message = `🆘 Что случилось?

Я постараюсь помочь, а если не получится — передам вопрос команде VenturaVPN ✨`;
        await replaceMessage(chatId, messageId, message, helpMenu);
      });
      break;
    }

    case 'about': {
      await simulateLoading(1000, async () => {
        const message = `✨ VenturaVPN

Свободный интернет без компромиссов.

🚀 Высокая скорость
🌍 Серверы по всему миру
🔓 Доступ к нужным сервисам

😎 И немного магии от Каролины`;
        await replaceMessage(chatId, messageId, message, mainMenu);
      });
      break;
    }

    case 'home': {
      await simulateLoading(800, async () => {
        const welcomeMessage = `Привет!`;
        await sendWelcomeMessages(chatId, messageId, welcomeMessage, 'Выбирай, что интересно:', STICKERS.WELCOME, mainMenu);
      });
      break;
    }

    case 'sub_1m':
    case 'sub_6m':
    case 'sub_12m':
    case 'renew':
    case 'key':
    case 'devices':
    case 'servers':
    case 'link_accounts':
    case 'help_key':
    case 'help_server':
    case 'help_payment':
    case 'human_support': {
      // Заглушки для остальных кнопок
      await simulateLoading(1000, async () => {
        await replaceMessage(chatId, messageId, 'Скоро здесь появится ответ! 😊', mainMenu);
      });
      break;
    }

    default:
      break;
  }
});

console.log('Бот Каролина запущен и готов к работе! 🚀');
