from datetime import datetime

import pytz
from discord.ext import commands
from requests import get

# https://discord.gg/VSK6vZN5 - сервер с ботом

# Как только Дискорд увидел свой токен на гитхабе, сразу же заблокировал его (( Придётся ваш использовать
BOT_TOKEN = 'ODM2MjEzNzc1NzMyMTc4OTc0.YIauxA.6u9KfqsImHOtsZ4MTmtTCeIDMoA' 
WEATHER_API_KEY = '88da3d26-75c3-4cdf-add0-d2ad53e5228b'
WEATHER_API_SERVER = 'https://api.weather.yandex.ru/v2/forecast'
API_GEOCODER = 'https://geocode-maps.yandex.ru/1.x/'
API_KEY_GEOCODER = '40d1649f-0493-4b70-98ba-98533de7710b'
HELP = '!place [адрес] - установить адрес, где узнать погоду\n' \
       '!current - узнать текущую погоду в заданном месте\n' \
       '!forecast [число не более 7] - показать прогноз погоды на заданное кол-во дней'


def get_coords_by_address(address: str):
    """Получение координат по адресу"""

    response = get(API_GEOCODER, params={'geocode': address,
                                         'apikey': API_KEY_GEOCODER, 'format': 'json'})

    if not response:
        raise Exception('Ошибка выполнения запроса:' +
                        f"Http статус: {response.status_code} ({response.reason})")

    toponym = response.json()["response"]["GeoObjectCollection"]["featureMember"]
    if not toponym:
        raise Exception('По данному адресу ничего не найдено!')

    toponym = toponym[0]["GeoObject"]
    coodrinates: list = toponym["Point"]["pos"].split()

    return coodrinates


def get_cur_weather(lon, lat):
    params = {'lat': lat, 'lon': lon, 'lang': 'ru_RU'}
    headers = {'X-Yandex-API-Key': WEATHER_API_KEY}

    response = get(WEATHER_API_SERVER, params=params, headers=headers)
    print(response.url)
    if not response:
        raise Exception('Ошибка выполнения запроса:' +
                        f"Http статус: {response.status_code} ({response.reason})")

    data = response.json()

    return data


class ForecastBot(commands.Cog):
    template = 'Current weather in {address} ' \
              '{time}\nTemperature: {temp}\n' \
              'Pressure: {press} mm\nHumidity: {humidity}\n' \
              '{condition}\nWind {wind_dir}, {speed} m/s'

    def __init__(self, bot):
        self.bot = bot
        self.data = {}

    @commands.command(name='help_bot')
    async def help(self, ctx):
        await ctx.send(HELP)

    @commands.command(name='place')
    async def set_place(self, ctx: commands.Context, address=None):
        if address is None:
            await ctx.send('Я вас не понимаю! Для справки введите !help_bot')
            return
        try:
            await ctx.send('Секунду... Я проверяю введённый адрес!\n')
            lon, lat = get_coords_by_address(address)
            self.data[(ctx.guild, ctx.channel)] = (address, (lon, lat))
            await ctx.send(f'Адрес успешно сменён на:\n\n{address}')

        except Exception as error:
            await ctx.send('Кажется, что-то пошло не так. Вот '
                           'что вышло:\n\n' + error.__str__())

    @commands.command(name='current')
    async def get_current_weather(self, ctx):
        if (ctx.guild, ctx.channel) not in self.data:
            await ctx.send('Вы не установили место, где узнавать погоду!')
            return

        try:
            address, coords = self.data[(ctx.guild, ctx.channel)]
            output = get_cur_weather(*coords)
            time_now = datetime.now(tz=pytz.timezone(output['info']['tzinfo']['name']))
            weather = output['fact']
            msg = ForecastBot.template.format(address=address,
                                              time=time_now.strftime("today"
                                                                     "%Y-%m-%d at time %H:%M"),
                                              temp=weather["temp"],
                                              press=weather["pressure_mm"],
                                              humidity=weather["humidity"],
                                              condition=weather["condition"],
                                              wind_dir=weather["wind_dir"],
                                              speed=weather["wind_speed"])
            await ctx.send(msg)
        except Exception as error:
            await ctx.send('Кажется, что-то пошло не так. Вот'
                           'что вышло:\n\n' + error.__str__())

    @commands.command(name='forecast')
    async def get_forecaset(self, ctx, days=None):
        if days is None or not days.isdigit():
            await ctx.send('Я вас не понимаю! Для справки введите !help_bot')
        days = min(7, int(days))
        address, coords = self.data[(ctx.guild, ctx.channel)]
        weather = get_cur_weather(*coords)
        msgs = []
        for d in weather['forecasts'][:days]:
            day = d['parts']['day']
            msgs.append(ForecastBot.template.format(address=address,
                                                    time=d['date'],
                                                    temp=day["temp_avg"],
                                                    press=day["pressure_mm"],
                                                    humidity=day["humidity"],
                                                    condition=day["condition"],
                                                    wind_dir=day["wind_dir"],
                                                    speed=day["wind_speed"]))
        await ctx.send('\n\n'.join(msgs))


bot = commands.Bot(command_prefix='!')
bot.add_cog(ForecastBot(bot))
bot.run(BOT_TOKEN)
