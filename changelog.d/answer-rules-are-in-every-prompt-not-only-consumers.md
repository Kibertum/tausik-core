<!-- lang: en -->
### Changed — the answer rules arrive before every answer

The answer rules shipped only into a generated consumer CLAUDE.md, and the prompt hook
spoke only after an answer had already run over budget. The UserPromptSubmit hook now
injects the full rules on every human prompt, before the answer is written; a test holds
the injected text byte-equal to the shipped block.

<!-- lang: ru -->
### Изменено — правила ответа приходят до каждого ответа

Правила ответа попадали только в сгенерированный CLAUDE.md проекта-потребителя, а хук
промпта говорил лишь после ответа, уже превысившего бюджет. Теперь хук UserPromptSubmit
подставляет правила целиком на каждый промпт человека, до ответа; тест держит
подставленный текст побайтно равным поставляемому блоку.
