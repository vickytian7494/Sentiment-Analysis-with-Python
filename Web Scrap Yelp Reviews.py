import csv
import requests
from bs4 import BeautifulSoup


# Personal Settings
enable_download = True
save_html = True
res_file_name = 'Yelp_reviews.csv'

def save_to_csv(result):
    print(f' Total number of reviews: {len(result)}')
    keys = result[0].keys()

    with open(res_file_name, 'w', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(result)


def get_reviews(url, result):
    if enable_download:
        response = requests.get(url)
        if response:  # it status code == 200
            soup = BeautifulSoup(response.text, 'html.parser')

            # this will save the result to HTML file if save_html is enabled.
            if save_html:
                with open("output1.html", "w", encoding='utf-8') as file:
                    file.write(str(soup))
    else:
        with open("output1.html", encoding='utf-8') as fp:
            soup = BeautifulSoup(fp, 'html.parser')


    def get_rating(element):
        stars = ["1__09f24__hRsgf", "2__09f24__zYaVU", "3__09f24__dlNly",
                 "4__09f24__zkZZV", "5__09f24__fJwXW"]
        rating = ''
        for star in stars:
            rating = element.find(
                "div", class_=f"i-stars__09f24__foihJ i-stars--regular-{star} border-color--default__09f24__NPAKY overflow--hidden__09f24___ayzG")
            if rating:
                rating = rating["aria-label"]
                break
        return rating

    all_reviews = soup.find_all(class_='undefined list__09f24__ynIEd')[8]
    for i in all_reviews:
        rating = get_rating(i)
        text = i.text
        date = i.find("span", class_="css-1e4fdj9").text
        name = i.find("a", class_="css-1422juy").text
        location = i.find("span", class_="css-1sufhje").text

        # print('Name: ', name)
        print(f'Name: {name}')
        print('Location: ', location)
        print('Rating: ', rating)
        print('Date: ', date)
        print('Review: ', text)
        print('*'*200, '\n')
        result.append({'Name': name, 'Location': location,
                      'Rating': rating, 'Date': date, 'Review': text})
    return result


def main():
    result = []
    urls = list(range(0, 400, 10))
    for url in urls:
        url = f'https://www.yelp.com/biz/the-ritz-carlton-half-moon-bay-half-moon-bay-2?start={url}'
        result = get_reviews(url, result)

    if result:
        save_to_csv(result)
    else:
        print('There is no result')


if __name__ == "__main__":
    main()


