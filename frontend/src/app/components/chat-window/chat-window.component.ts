import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-chat-window',
  templateUrl: './chat-window.component.html',
  styleUrls: ['./chat-window.component.css'],
})
export class ChatWindowComponent {
  messages: any[] = [];
  userInput: string = '';

  constructor(private http: HttpClient) {}

  sendMessage() {
    if (!this.userInput.trim()) return;

    const question = this.userInput;

    this.messages.push({ role: 'user', text: question });

    this.userInput = '';

    this.http
      .post('http://localhost:8000/hybrid-ask', {
        question,
      })
      .subscribe((res: any) => {
        this.messages.push({
          role: 'bot',
          text: res.answer,
        });

        // auto scroll
        setTimeout(() => {
          const container = document.querySelector('.messages');
          if (container) container.scrollTop = container.scrollHeight;
        }, 100);
      });
  }
}
