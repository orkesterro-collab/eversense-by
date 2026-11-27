<?php
// Contact form for the Belarus representative. The destination is fixed server-side.
const CONTACT_RECIPIENT = '6713971@gmail.com';
const CONTACT_SENDER = 'site@eversense.by';
const CONTACT_COOLDOWN = 60;

header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

function respond($status, $message)
{
    http_response_code($status);
    if (strpos($_SERVER['HTTP_ACCEPT'] ?? '', 'application/json') !== false) {
        header('Content-Type: application/json; charset=UTF-8');
        echo json_encode(['ok' => $status === 200, 'message' => $message], JSON_UNESCAPED_UNICODE);
    } elseif ($status === 200) {
        header('Location: ../../contacts.html#cooperation-sent', true, 303);
    } else {
        header('Content-Type: text/html; charset=UTF-8');
        $detail = htmlspecialchars($message, ENT_QUOTES, 'UTF-8');
        echo '<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            . '<title>Сотрудничество — EVERSENSE</title><link rel="stylesheet" href="../buyer.css">'
            . '<body class="ev-buyer"><main class="ev-wrap ev-prose"><h1>Сотрудничество</h1><p>' . $detail . '</p>'
            . '<p><a class="ev-button" href="../../contacts.html#cooperation">Вернуться к форме</a></p>'
            . '<p><a href="tel:+375296713971">+375 29 671-39-71</a></p></main></body></html>';
    }
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Allow: POST');
    respond(405, 'Отправьте обращение через форму на странице контактов.');
}
if ((int) ($_SERVER['CONTENT_LENGTH'] ?? 0) > 65536) {
    respond(413, 'Сократите сообщение до 3000 символов.');
}

function field($key)
{
    $value = $_POST[$key] ?? '';
    if (!is_string($value)) {
        respond(422, 'Проверьте поля формы и повторите отправку.');
    }
    $value = preg_replace('/\A[\s\p{Z}]+|[\s\p{Z}]+\z/u', '', $value);
    if ($value === null) {
        respond(422, 'Проверьте поля формы и повторите отправку.');
    }
    return $value;
}

$name = field('name');
// A previously opened contact page can still post the old email field.
$contact = field(array_key_exists('contact', $_POST) ? 'contact' : 'email');
$message = str_replace(["\r\n", "\r"], "\n", field('message'));
if (field('website') !== '') {
    respond(422, 'Проверьте поля формы и повторите отправку.');
}
if (!preg_match('/\A[^\p{Cc}]{1,120}\z/u', $name)) {
    respond(422, 'Введите имя или название компании (до 120 символов).');
}
$isEmail = !preg_match('/[\x00-\x1f\x7f]/', $contact) && filter_var($contact, FILTER_VALIDATE_EMAIL);
$phoneNumber = preg_replace('/[\p{Zs}\p{Pd}().]/u', '', $contact);
if (strlen($contact) > 254 || (!$isEmail && !preg_match('/\A\+?[0-9]{7,15}\z/', $phoneNumber))) {
    respond(422, 'Укажите электронную почту или номер телефона для ответа.');
}
if (!preg_match('/\A.{1,3000}\z/su', $message) || preg_match('/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/', $message)) {
    respond(422, 'Введите сообщение длиной до 3000 символов.');
}

// Serialize sends from the same visitor, including a double tap or network retry.
$unavailable = 'Сейчас не удалось отправить сообщение. Попробуйте позже или позвоните по телефону +375 29 671-39-71.';
$directory = sys_get_temp_dir() . '/eversense-contact-' . substr(hash('sha256', __DIR__), 0, 16);
if (!is_dir($directory) && !@mkdir($directory, 0700) && !is_dir($directory)) {
    respond(503, $unavailable);
}
$key = hash('sha256', $_SERVER['REMOTE_ADDR'] ?? '');
$lock = @fopen($directory . '/' . $key, 'c+');
if (!$lock || !flock($lock, LOCK_EX)) {
    respond(503, $unavailable);
}
$now = time();
$remaining = (int) stream_get_contents($lock) + CONTACT_COOLDOWN - $now;
if ($remaining > 0) {
    header('Retry-After: ' . $remaining);
    respond(429, 'Вы уже отправили сообщение. Следующее можно отправить через минуту.');
}
rewind($lock);
if (!ftruncate($lock, 0) || !fwrite($lock, (string) $now) || !fflush($lock)) {
    respond(503, $unavailable);
}

$body = "Обращение по вопросам сотрудничества с eversense.by\r\n\r\n";
$body .= "Имя или компания: $name\r\n";
$contactLabel = $isEmail ? 'Электронная почта для ответа' : 'Телефон для ответа';
$body .= "$contactLabel: $contact\r\n\r\n" . str_replace("\n", "\r\n", $message);
$subject = '=?UTF-8?B?' . base64_encode('EVERSENSE — сотрудничество') . '?=';
$headers = [
    'From: EVERSENSE <' . CONTACT_SENDER . '>',
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    'Content-Transfer-Encoding: base64',
];
if ($isEmail) {
    $headers[] = 'Reply-To: ' . $contact;
}
$accepted = function_exists('mail') && @mail(
    CONTACT_RECIPIENT, $subject, chunk_split(base64_encode($body)), implode("\r\n", $headers), '-f' . CONTACT_SENDER
);
if (!$accepted) {
    ftruncate($lock, 0);
}
fclose($lock);
respond($accepted ? 200 : 503, $accepted ? 'Спасибо! Сообщение отправлено.' : $unavailable);
