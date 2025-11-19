import requests

url = "https://api.themoviedb.org/3/authentication"

headers = {
    "accept": "application/json",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJmZWExYjkxNWQyYzkxYzJjMzA1ZmNkNzNiYWI3YjM2MyIsIm5iZiI6MTc2MzQ2MzU4MS43MTIsInN1YiI6IjY5MWM1MTlkZDQ3Y2Q4OTczYzZkOTk4NiIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.ouq8E8Nz11K2-V1y_AMqfgIlb-pux2UzvOK1Zwzt0pY"
}

response = requests.get(url, headers=headers)

print(response.text)
