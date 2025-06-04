SELECT artist, COUNT(*) AS nb_tracks
FROM items
GROUP BY artist
ORDER BY nb_tracks DESC
LIMIT 10;