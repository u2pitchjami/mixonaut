-- 1️⃣ Items SANS audio_features (id présent dans items, absent dans audio_features)
SELECT COUNT(*) AS nb_items_sans_audio
FROM items
WHERE id NOT IN (
    SELECT id FROM audio_features
);

SELECT id, path
FROM items
WHERE id NOT IN (
    SELECT id FROM audio_features
);

-- 2️⃣ audio_features SANS item correspondant (id présent dans audio_features, absent dans items)
SELECT COUNT(*) AS nb_audio_orphelins
FROM audio_features
WHERE id NOT IN (
    SELECT id FROM items
);

SELECT id
FROM audio_features
WHERE id NOT IN (
    SELECT id FROM items
);
