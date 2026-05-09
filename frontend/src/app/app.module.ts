import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { LayoutComponent } from './components/layout/layout.component';
import { DocumentSidebarComponent } from './components/document-sidebar/document-sidebar.component';
import { ChatWindowComponent } from './components/chat-window/chat-window.component';
import { ChatMessageComponent } from './components/chat-message/chat-message.component';

@NgModule({
  declarations: [
    AppComponent,
    LayoutComponent,
    DocumentSidebarComponent,
    ChatWindowComponent,
    ChatMessageComponent,
  ],
  imports: [BrowserModule, AppRoutingModule, FormsModule, HttpClientModule],
  providers: [],
  bootstrap: [AppComponent],
})
export class AppModule {}
