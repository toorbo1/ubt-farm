// Тест для проверки логики подписки
const assert = require('assert');

// Имитация userData
const userData = {};

// Функция проверки статуса подписки пользователя
function getUserSubscriptionStatus(userId) {
  const user = userData[userId];
  if (!user || !user.subscription) {
    return 'none'; // Нет подписки
  }

  const now = new Date();
  const endDate = new Date(user.subscription.endDate);

  if (now > endDate) {
    return 'expired'; // Подписка истекла
  }

  return 'active'; // Подписка активна
}

// Тесты
console.log('🧪 Тестирование логики подписки\n');

// Тест 1: Новый пользователь без подписки
console.log('Тест 1: Пользователь без подписки');
const status1 = getUserSubscriptionStatus('user123');
assert.strictEqual(status1, 'none', 'Должен быть статус "none"');
console.log('✅ Пройден: статус "none"\n');

// Тест 2: Пользователь с активной подпиской
console.log('Тест 2: Пользователь с активной подпиской');
const futureDate = new Date();
futureDate.setMonth(futureDate.getMonth() + 1);
userData['user456'] = {
  subscription: {
    duration: 30,
    devices: 5,
    endDate: futureDate.toISOString()
  }
};
const status2 = getUserSubscriptionStatus('user456');
assert.strictEqual(status2, 'active', 'Должен быть статус "active"');
console.log('✅ Пройден: статус "active"\n');

// Тест 3: Пользователь с истекшей подпиской
console.log('Тест 3: Пользователь с истекшей подпиской');
const pastDate = new Date();
pastDate.setMonth(pastDate.getMonth() - 1);
userData['user789'] = {
  subscription: {
    duration: 30,
    devices: 5,
    endDate: pastDate.toISOString()
  }
};
const status3 = getUserSubscriptionStatus('user789');
assert.strictEqual(status3, 'expired', 'Должен быть статус "expired"');
console.log('✅ Пройден: статус "expired"\n');

// Тест 4: Форматирование даты
console.log('Тест 4: Форматирование даты');
function formatEndDate(endDate) {
  const date = new Date(endDate);
  const options = { day: 'numeric', month: 'long', year: 'numeric' };
  return date.toLocaleDateString('ru-RU', options);
}

const testDate = new Date('2026-09-05T00:00:00Z');
const formatted = formatEndDate(testDate);
console.log(`Отформатированная дата: ${formatted}`);
assert.ok(formatted.includes('5') || formatted.includes('05'), 'Должно содержать день');
assert.ok(formatted.length > 10, 'Должно быть отформатировано');
console.log('✅ Пройден: форматирование даты\n');

console.log('🎉 Все тесты пройдены!');
