from time import sleep
from random import choice


def write_bubble(text_of_old_bubble, text_for_new_bubble, time_to_wait_for_future):
    htmlstring: str = f"""
        <!DOCTYPE html>
        <meta http-equiv="refresh" content="{time_to_wait_for_future}" >
        <html>

        <head>
            <link rel="stylesheet" href="bubbles.css">
        </head>

        <body>

            <section class="chat">

                <div class="chat__message chat__message_B" style="--delay: 0s;">
                    <div class="chat__content">
                        <p>{text_for_new_bubble}</p>
                    </div>
                </div>

                <div class="chat__message chat__message_B" style="--delay: -1s;">
                    <div class="chat__content">
                        <p>{text_of_old_bubble}</p>
                    </div>
                </div>


            </section>

        </body>

        </html>
    """
    with open('bubbles.html', 'w') as htmlwriter:
        htmlwriter.write(htmlstring)


def write_css():
    css_string: str = """
    body { 
        background-color: transparent;
    }

    *, *::before {
    box-sizing: border-box;
    }

    .chat {
    display: flex;
    flex-direction: column-reverse;
    height: 12rem;
    overflow: hidden;
    border: hidden;
    font: .85rem/1.5 Arial;
    color: #313131;
    position: relative;
    }

    .chat p {
    margin: 0;
    padding: 0;
    }

    .chat__content {
    flex: 0 1 auto;
    padding: 1rem;
    margin: 0 0.5rem;
    background: var(--bgcolor);
    border-radius: var(--radius);
    }

    .chat__message {
    width: 45%;
    display: flex;
    align-items: flex-end;
    transform-origin: 0 100%;
    padding-top: 0;
    transform: scale(0);
    max-height: 0;
    overflow: hidden;
    animation: message 0.15s ease-out 0s forwards;
    animation-delay: var(--delay);
    --bgcolor: #ffbbce;
    --radius: 8px 8px 8px 0;
    }

    .chat__message_B {
    flex-direction: row-reverse;
    text-align: right;
    align-self: flex-end;
    transform-origin: 100% 100%;
    --bgcolor: #ffbbce;
    --radius: 8px 8px 0 8px;
    }

    @keyframes message {
    0% {
        max-height: 100vmax;
    }
    80% {
        transform: scale(1.1);
    }
    100% {
        transform: scale(1);
        max-height: 100vmax;
        overflow: visible;
        padding-top: 1rem;
    }
    }

    """
    with open("bubbles.css", "w") as csswriter:
        csswriter.write(css_string)


if __name__ == "__main__":
    write_css()
    current_bubble = "Initial text!"
    while(True):
        old_bubble = current_bubble
        current_bubble = choice(['We switched to scene 1!', 'Oops, waited too long', 'Hey, something new!',
                                'Time to change view :)', 'Sorry, I took my time :(', 'Enjoy this new scene!'])
        time_to_wait = choice([3, 6, 9])
        write_bubble(old_bubble, current_bubble, time_to_wait)
        sleep(time_to_wait)
