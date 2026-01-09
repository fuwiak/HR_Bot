#!/usr/bin/env python3
"""Скрипт для исправления индентации в callback_router.py"""
import re

with open('telegram_bot/handlers/menu/callback_router.py', 'r') as f:
    lines = f.readlines()

# Исправляем строки 464-470 (индексы 463-469)
for i in range(463, min(470, len(lines))):
    line = lines[i]
    stripped = line.lstrip()
    
    if i == 463:  # if not projects:
        # Должно быть: 16 пробелов (4 уровня внутри try)
        lines[i] = '            if not projects:\n'
    elif i == 464:  # keyboard = ...
        # Должно быть: 20 пробелов (5 уровней - внутри if)
        lines[i] = '                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_projects")]]\n'
    elif i in [465, 466, 467, 468, 469]:  # await и остальное внутри if
        # Должно быть: 20 пробелов (5 уровней)
        if stripped:
            lines[i] = '                ' + stripped

# Исправляем строки 485-490 (индексы 484-489) - await должен быть внутри try
for i in range(484, min(490, len(lines))):
    line = lines[i]
    stripped = line.lstrip()
    
    if i == 484:  # пустая строка
        continue
    elif i == 485:  # await query.edit_message_text(
        # Должно быть: 16 пробелов (4 уровня - внутри try, но после if)
        lines[i] = '            await query.edit_message_text(\n'
    elif i in [486, 487, 488, 489]:  # остальные строки await блока
        if stripped:
            # Должно быть: 16 пробелов для первой строки, 20 для остальных
            if i == 486:
                lines[i] = '                ' + stripped
            else:
                lines[i] = '                ' + stripped

with open('telegram_bot/handlers/menu/callback_router.py', 'w') as f:
    f.writelines(lines)

print("✅ Индентация исправлена")
